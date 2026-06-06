"""
AgriBazaar — prophet_engine.py
Facebook Prophet time-series forecasting for 6-month crop price predictions.

Prophet decomposes prices into:
  - Trend        : long-term upward/downward movement
  - Seasonality  : yearly crop cycle (cheap in harvest, expensive off-season)
  - Changepoints : sudden market shifts (detected automatically)

Models are trained on demand per (crop, city) and cached in memory.
Falls back to Holt-Winters, then historical averages if Prophet unavailable.
"""
import threading
import logging

logger = logging.getLogger(__name__)

_model_cache: dict = {}
_cache_lock = threading.Lock()
MIN_ROWS = 60


# ── Availability ──────────────────────────────────────────────────────────────

def is_available() -> bool:
    try:
        from prophet import Prophet          # noqa
        import cmdstanpy
        cmdstanpy.cmdstan_path()             # raises if CmdStan not found
        return True
    except Exception:
        return False


def _hw_available() -> bool:
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing  # noqa
        return True
    except ImportError:
        return False


# ── Data preparation ──────────────────────────────────────────────────────────

def _get_daily_df(crop: str, city: str):
    """Returns a DataFrame with columns ['ds','y'] ready for Prophet, or None."""
    try:
        from . import data_loader as dl
        import pandas as pd

        df  = dl._df()
        sub = df[(df['crop'] == crop) & (df['city'] == city)].copy()
        if len(sub) < MIN_ROWS:
            return None

        daily = sub.groupby('date')['avg_price'].mean().reset_index()
        daily.columns = ['ds', 'y']
        daily['ds'] = pd.to_datetime(daily['ds'])
        daily = daily.sort_values('ds').dropna()
        return daily if len(daily) >= MIN_ROWS else None

    except Exception as e:
        logger.error(f"[Prophet] Data prep failed {crop}/{city}: {e}")
        return None


def _get_monthly_series(crop: str, city: str):
    """Returns a monthly pandas Series for Holt-Winters fallback, or None."""
    try:
        from . import data_loader as dl
        import pandas as pd

        df  = dl._df()
        sub = df[(df['crop'] == crop) & (df['city'] == city)].copy()
        if len(sub) < MIN_ROWS:
            return None

        daily = sub.groupby('date')['avg_price'].mean()
        daily.index = pd.to_datetime(daily.index)
        daily = daily.sort_index().resample('D').mean().ffill().dropna()
        monthly = daily.resample('MS').mean().dropna()
        return monthly if len(monthly) >= 12 else None

    except Exception as e:
        logger.error(f"[Prophet] Monthly prep failed {crop}/{city}: {e}")
        return None


# ── Model training ────────────────────────────────────────────────────────────

def _train_prophet(crop: str, city: str):
    """Train a Prophet model. Returns fitted model or None."""
    try:
        from prophet import Prophet
        import logging as _log
        # Suppress Prophet's verbose Stan output
        _log.getLogger('prophet').setLevel(_log.WARNING)
        _log.getLogger('cmdstanpy').setLevel(_log.WARNING)

        daily = _get_daily_df(crop, city)
        if daily is None:
            return None

        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode='multiplicative',  # % swings scale with price level
            changepoint_prior_scale=0.05,       # conservative — avoids overfitting
            interval_width=0.80,                # 80% confidence bands
        )
        model.fit(daily)
        logger.info(f"[Prophet] Trained for {crop}/{city} ({len(daily)} rows)")
        return model

    except Exception as e:
        logger.error(f"[Prophet] Training failed {crop}/{city}: {e}")
        return None


def _train_holtwinters(crop: str, city: str):
    """Holt-Winters fallback. Returns (model, monthly_series) or (None, None)."""
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        monthly = _get_monthly_series(crop, city)
        if monthly is None:
            return None, None

        model = ExponentialSmoothing(
            monthly,
            trend='add',
            seasonal='add',
            seasonal_periods=12,
            damped_trend=True,
            initialization_method='estimated',
        ).fit(optimized=True, use_brute=False)

        logger.info(f"[HW] Trained for {crop}/{city} ({len(monthly)} months)")
        return model, monthly

    except Exception as e:
        logger.error(f"[HW] Training failed {crop}/{city}: {e}")
        return None, None


def _get_cached(crop: str, city: str):
    """Returns cached (prophet_model_or_None, hw_model_or_None, hw_series_or_None)."""
    key = f"{crop}||{city}"
    if key in _model_cache:
        return _model_cache[key]

    with _cache_lock:
        if key not in _model_cache:
            prophet_m = None
            hw_m, hw_s = None, None

            if is_available():
                prophet_m = _train_prophet(crop, city)

            if prophet_m is None and _hw_available():
                hw_m, hw_s = _train_holtwinters(crop, city)

            _model_cache[key] = (prophet_m, hw_m, hw_s)

        return _model_cache[key]


# ── Public API ────────────────────────────────────────────────────────────────

def get_6month_forecast(crop: str, city: str, start_month_idx: int) -> list | None:
    """
    Returns 6 month dicts with price predictions + confidence bands.
    Uses Prophet if available, Holt-Winters otherwise, None if both fail.

    Each dict keys:
        month_index, prophet_price, prophet_upper, prophet_lower,
        confidence_pct, interval_pct, using_prophet
    """
    prophet_m, hw_m, hw_s = _get_cached(crop, city)

    # ── Prophet path ──────────────────────────────────────────────────────────
    if prophet_m is not None:
        try:
            from . import data_loader as dl
            import pandas as pd

            last_date = dl._df()['date'].max()
            future    = prophet_m.make_future_dataframe(periods=210, freq='D')
            fc        = prophet_m.predict(future)
            fc_future = fc[fc['ds'] > pd.Timestamp(last_date)].copy()

            if fc_future.empty:
                raise ValueError("No future rows in forecast")

            fc_future['month_num'] = fc_future['ds'].dt.month   # 1-based

            results = []
            for i in range(6):
                mi  = (start_month_idx + i) % 12    # 0-based
                mn  = mi + 1                          # 1-based calendar month

                rows = fc_future[fc_future['month_num'] == mn]
                if rows.empty:
                    rows = fc_future.iloc[i*28:(i+1)*28]

                yhat  = max(1, int(round(rows['yhat'].mean())))
                upper = max(1, int(round(rows['yhat_upper'].mean())))
                lower = max(1, int(round(rows['yhat_lower'].mean())))

                interval_pct = (upper - lower) / max(yhat, 1) * 100
                confidence   = max(45, min(95, int(100 - interval_pct * 0.7)))

                results.append({
                    'month_index'   : mi,
                    'prophet_price' : yhat,
                    'prophet_upper' : upper,
                    'prophet_lower' : lower,
                    'confidence_pct': confidence,
                    'interval_pct'  : round(interval_pct, 1),
                    'using_prophet' : True,
                    'engine'        : 'prophet',
                })

            logger.info(f"[Prophet] Forecast served for {crop}/{city}")
            return results

        except Exception as e:
            logger.error(f"[Prophet] Forecast failed {crop}/{city}: {e}")
            # Fall through to Holt-Winters

    # ── Holt-Winters fallback ─────────────────────────────────────────────────
    if hw_m is not None and hw_s is not None:
        try:
            fc = hw_m.forecast(6)
            try:
                sim   = hw_m.simulate(6, repetitions=300, error='add')
                upper = sim.quantile(0.90, axis=1)
                lower = sim.quantile(0.10, axis=1)
            except Exception:
                upper = fc * 1.15
                lower = fc * 0.85

            results = []
            for i in range(6):
                mi         = (start_month_idx + i) % 12
                yhat       = max(1, int(round(float(fc.iloc[i]))))
                yhat_upper = max(1, int(round(float(upper.iloc[i]))))
                yhat_lower = max(1, int(round(float(lower.iloc[i]))))

                interval_pct = (yhat_upper - yhat_lower) / max(yhat, 1) * 100
                confidence   = max(40, min(90, int(100 - interval_pct * 0.7)))

                results.append({
                    'month_index'   : mi,
                    'prophet_price' : yhat,
                    'prophet_upper' : yhat_upper,
                    'prophet_lower' : yhat_lower,
                    'confidence_pct': confidence,
                    'interval_pct'  : round(interval_pct, 1),
                    'using_prophet' : True,
                    'engine'        : 'holtwinters',
                })

            logger.info(f"[HW] Forecast served for {crop}/{city}")
            return results

        except Exception as e:
            logger.error(f"[HW] Forecast failed {crop}/{city}: {e}")

    return None  # both failed — ai_engine uses historical averages


def clear_cache(crop: str = None, city: str = None):
    global _model_cache
    with _cache_lock:
        if crop and city:
            _model_cache.pop(f"{crop}||{city}", None)
        else:
            _model_cache.clear()


def warmup(crop: str, city: str):
    """Pre-train in background."""
    threading.Thread(target=_get_cached, args=(crop, city), daemon=True).start()
