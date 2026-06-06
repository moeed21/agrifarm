"""
AgriBazaar — ml_engine.py
==========================
Machine learning price prediction engine.
Wraps the trained model from data_engine.py and exposes
prediction helpers used internally.

Note: The primary ML logic lives in data_engine.py (_train_model).
This module provides a clean prediction interface on top of that.
"""
from datetime import datetime
from . import data_engine as _de


def predict_price(crop: str, city: str, month_index: int = None) -> float:
    """
    Predict the price of a crop in a city for a given month (0=Jan, 11=Dec).
    Falls back to historical monthly average if model is unavailable.
    """
    if month_index is None:
        month_index = datetime.now().month - 1

    try:
        model = _de.get_model()
        df = _de.get_df()
        if model is not None and df is not None:
            # Use historical data to form a feature row
            le = _de._le
            city_enc = le['city'].transform([city])[0] if city in le['city'].classes_ else 0
            crop_enc = le['crop'].transform([crop])[0] if crop in le['crop'].classes_ else 0

            import numpy as np
            # Build a feature vector using typical lag values for this crop/city
            monthly = _de.get_monthly_prices(crop, city)
            cur = monthly[month_index] if monthly else 100
            lag1  = monthly[(month_index - 1) % 12] if monthly else cur
            lag3  = monthly[(month_index - 3) % 12] if monthly else cur
            lag6  = monthly[(month_index - 6) % 12] if monthly else cur

            import math
            features = np.array([[
                lag1, lag3, lag6, lag1, lag1, lag3,          # lag_1, lag_3, lag_6, lag_7, lag_14, lag_30
                abs(cur - lag1), abs(cur - lag3),             # volatility_3, volatility_6
                month_index + 1,                              # month
                math.sin(2 * math.pi * (month_index + 1) / 12),  # month_sin
                math.cos(2 * math.pi * (month_index + 1) / 12),  # month_cos
                (month_index // 3) + 1,                       # quarter
                datetime.now().year,                          # year
                city_enc, crop_enc, 0,                        # city_encoded, crop_encoded, market_encoded
            ]])
            pred = model.predict(features)[0]
            return round(float(pred), 1)
    except Exception:
        pass

    # Fallback to monthly average from data_engine
    try:
        monthly = _de.get_monthly_prices(crop, city)
        if monthly:
            return float(monthly[month_index])
    except Exception:
        pass

    return float(_de._fallback_monthly(crop, city)[month_index])


def predict_next_months(crop: str, city: str, start_month: int, n: int = 6) -> list:
    """
    Return predicted prices for the next `n` months starting from `start_month`.
    Returns list of {'month_index': int, 'month_name': str, 'price': float}
    """
    MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    result = []
    for i in range(n):
        m = (start_month + i) % 12
        price = predict_price(crop, city, m)
        result.append({
            'month_index': m,
            'month_name':  MONTHS[m],
            'price':       price,
        })
    return result
