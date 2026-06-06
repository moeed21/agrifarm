"""
AgriBazaar — weather.py
Fetches REAL weather data from Open-Meteo (free, no API key needed).
- Current + 16-day forecast: /v1/forecast
- Historical climate normals (up to 12 months): /v1/climate  (1991-2020 baseline)
Falls back to Pakistan Met Dept 30-year climatological averages only when
Open-Meteo is completely unreachable.
"""

import urllib.request
import json
import threading
import calendar
from datetime import datetime, timedelta

# ── CITY COORDINATES ─────────────────────────────────────────────────────────
CITY_COORDS = {
    'Karachi':    {'lat': 24.8607, 'lon': 67.0011},
    'Lahore':     {'lat': 31.5204, 'lon': 74.3587},
    'Multan':     {'lat': 30.1978, 'lon': 71.4711},
    'Faislabad':  {'lat': 31.4504, 'lon': 73.1350},
    'Sialkot':    {'lat': 32.4945, 'lon': 74.5229},
    'Quetta':     {'lat': 30.1798, 'lon': 66.9750},
    'Peshawer':   {'lat': 34.0151, 'lon': 71.5249},
    'Rawalpindi': {'lat': 33.6007, 'lon': 73.0679},
    'Islamabad':  {'lat': 33.6844, 'lon': 73.0479},
}

# ── FALLBACK: Pakistan Met Dept 30-year climatological averages ───────────────
FALLBACK_RAINFALL = {
    'Karachi':    [5,  10, 5,  2,  1,  18, 81,  41,  13,  2,  2,  5],
    'Lahore':     [25, 32, 36, 18, 18, 38, 220, 241, 94,  10, 5,  18],
    'Multan':     [8,  12, 15, 8,  10, 15, 55,  41,  18,  5,  3,  7],
    'Faislabad':  [18, 22, 28, 12, 12, 25, 150, 160, 70,  8,  4,  12],
    'Sialkot':    [45, 55, 68, 35, 35, 75, 350, 380, 180, 28, 12, 35],
    'Quetta':     [35, 40, 55, 28, 18, 8,  12,  10,  5,   8,  18, 32],
    'Peshawer':   [48, 58, 72, 38, 22, 15, 25,  35,  15,  8,  18, 42],
    'Rawalpindi': [58, 68, 88, 48, 38, 58, 280, 310, 145, 20, 15, 48],
    'Islamabad':  [58, 68, 88, 48, 38, 58, 290, 320, 148, 20, 15, 48],
}
FALLBACK_TEMP = {
    'Karachi':    [25, 27, 31, 34, 36, 36, 34, 33, 33, 35, 32, 27],
    'Lahore':     [19, 22, 28, 35, 40, 42, 38, 37, 35, 32, 26, 20],
    'Multan':     [17, 20, 27, 35, 41, 44, 41, 39, 36, 33, 26, 19],
    'Faislabad':  [18, 21, 27, 35, 40, 42, 39, 38, 35, 32, 26, 19],
    'Sialkot':    [17, 20, 26, 33, 38, 39, 34, 33, 31, 29, 24, 18],
    'Quetta':     [8,  11, 17, 22, 27, 32, 34, 33, 28, 22, 14, 9],
    'Peshawer':   [14, 18, 24, 30, 36, 41, 39, 37, 34, 29, 22, 15],
    'Rawalpindi': [15, 18, 24, 31, 36, 39, 34, 33, 30, 27, 21, 16],
    'Islamabad':  [15, 18, 24, 31, 36, 39, 34, 33, 30, 27, 21, 16],
}

# ── IN-MEMORY CACHE ───────────────────────────────────────────────────────────
_cache = {}
_lock  = threading.Lock()
CACHE_TTL         = 3600       # 1 hour for forecast
CACHE_TTL_CLIMATE = 86400 * 7  # 7 days for climate normals (rarely change)


def _fetch_url(url, timeout=8):
    """Fetch JSON from URL. Returns dict or None."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AgriBazaar/2.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"⚠️  Weather fetch failed: {e}")
        return None


# ── 1. LIVE FORECAST (current month) ─────────────────────────────────────────

def get_current_weather_fast(city):
    """
    Fast current weather using wttr.in JSON API.
    Much faster than Open-Meteo for current conditions.
    Returns dict with temp, rain, description or None.
    Cached for 30 minutes.
    """
    coords = CITY_COORDS.get(city)
    if not coords:
        return None
    cache_key = f"wttr_{city}"
    with _lock:
        cached = _cache.get(cache_key)
        if cached and (datetime.now() - cached["ts"]).seconds < 1800:
            return cached["data"]
    url = f"https://wttr.in/{coords['lat']},{coords['lon']}?format=j1"
    data = _fetch_url(url, timeout=4)
    if not data:
        return None
    try:
        cur = data["current_condition"][0]
        desc = cur["weatherDesc"][0]["value"]
        result = {
            "available": True,
            "city": city,
            "temp_max": float(cur["temp_C"]),
            "temp_min": float(cur["temp_C"]) - 5,
            "precip_mm": float(cur["precipMM"]),
            "rain_prob": int(cur.get("chanceofrain", 0)),
            "humidity": int(cur["humidity"]),
            "description": desc,
            "source": "wttr.in",
            "date": str(datetime.now().date()),
            "wind_kmph": cur.get("windspeedKmph", "—"),
        }
        with _lock:
            _cache[cache_key] = {"data": result, "ts": datetime.now()}
        print(f"Fast weather OK for {city}: {desc}")
        return result
    except Exception as e:
        print(f"wttr.in parse error: {e}")
        return None

def get_forecast_16day(city):
    """
    Fetch 16-day daily forecast from Open-Meteo /v1/forecast.
    Returns dict with list of daily records, or None on failure.
    Cached for 1 hour.
    """
    coords = CITY_COORDS.get(city)
    if not coords:
        return None

    cache_key = f"forecast_{city}"
    with _lock:
        cached = _cache.get(cache_key)
        if cached and (datetime.now() - cached['ts']).seconds < CACHE_TTL:
            return cached['data']

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={coords['lat']}&longitude={coords['lon']}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"precipitation_probability_max,weathercode"
        f"&forecast_days=16"
        f"&timezone=Asia%2FKarachi"
    )
    data = _fetch_url(url)
    if not data or 'daily' not in data:
        return None

    daily = data['daily']
    result = {'source': 'open-meteo-forecast', 'city': city, 'days': []}
    for i, date in enumerate(daily.get('time', [])):
        result['days'].append({
            'date':      date,
            'temp_max':  daily.get('temperature_2m_max',  [None]*20)[i],
            'temp_min':  daily.get('temperature_2m_min',  [None]*20)[i],
            'precip_mm': daily.get('precipitation_sum',   [0]*20)[i] or 0,
            'rain_prob': daily.get('precipitation_probability_max', [0]*20)[i] or 0,
            'wcode':     daily.get('weathercode',         [0]*20)[i] or 0,
        })

    with _lock:
        _cache[cache_key] = {'data': result, 'ts': datetime.now()}
    print(f"✅ Open-Meteo 16-day forecast fetched for {city}")
    return result


# ── 2. HISTORICAL MONTHLY AVERAGES (months 1-11 out) ─────────────────────────

def _get_historical_monthly_avg(city, month_index, year=None):
    """
    Fetch actual historical daily data for a specific month from Open-Meteo
    /v1/archive and average it. Uses the most recent available complete year
    for that month. Cached for 7 days.
    """
    coords = CITY_COORDS.get(city)
    if not coords:
        return None

    now = datetime.now()
    # Determine the most recent full year for the requested month
    if year is None:
        # Use prior year if month hasn't finished yet this year
        target_year = now.year - 1 if (month_index + 1) >= now.month else now.year
    else:
        target_year = year

    cache_key = f"hist_{city}_{month_index}_{target_year}"
    with _lock:
        cached = _cache.get(cache_key)
        if cached and (datetime.now() - cached['ts']).seconds < CACHE_TTL_CLIMATE:
            return cached['data']

    month_num = month_index + 1
    last_day  = calendar.monthrange(target_year, month_num)[1]
    start     = f"{target_year}-{month_num:02d}-01"
    end       = f"{target_year}-{month_num:02d}-{last_day:02d}"

    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={coords['lat']}&longitude={coords['lon']}"
        f"&start_date={start}&end_date={end}"
        f"&daily=temperature_2m_max,precipitation_sum"
        f"&timezone=Asia%2FKarachi"
    )
    data = _fetch_url(url, timeout=10)
    if not data or 'daily' not in data:
        return None

    daily  = data['daily']
    temps  = [t for t in daily.get('temperature_2m_max', []) if t is not None]
    precip = [p for p in daily.get('precipitation_sum', []) if p is not None]

    if not temps:
        return None

    result = {
        'temp_c':      round(sum(temps) / len(temps), 1),
        'rainfall_mm': round(sum(precip), 1),   # total for the month
        'source':      f'open-meteo-archive-{target_year}',
    }
    with _lock:
        _cache[cache_key] = {'data': result, 'ts': datetime.now()}
    print(f"✅ Open-Meteo archive {city} month={month_num} year={target_year}")
    return result


# ── 3. CLIMATE NORMALS (long-range stable baseline) ───────────────────────────

def _fetch_climate_normals(city, month_index):
    """
    Fetch 30-year climate normals from Open-Meteo climate API (1991-2020).
    Returns {'temp_c', 'rainfall_mm'} or None.
    Cached for 7 days.
    """
    coords = CITY_COORDS.get(city)
    if not coords:
        return None

    cache_key = f"climate_{city}_{month_index}"
    with _lock:
        cached = _cache.get(cache_key)
        if cached and (datetime.now() - cached['ts']).seconds < CACHE_TTL_CLIMATE:
            return cached['data']

    month_num = month_index + 1
    last_day  = calendar.monthrange(2020, month_num)[1]
    start     = f"1991-{month_num:02d}-01"
    end       = f"2020-{month_num:02d}-{last_day:02d}"

    url = (
        f"https://climate-api.open-meteo.com/v1/climate"
        f"?latitude={coords['lat']}&longitude={coords['lon']}"
        f"&start_date={start}&end_date={end}"
        f"&models=EC_Earth3P_HR"
        f"&daily=temperature_2m_mean,precipitation_sum"
    )
    data = _fetch_url(url, timeout=10)
    if not data or 'daily' not in data:
        return None

    daily  = data['daily']
    temps  = [t for t in daily.get('temperature_2m_mean', []) if t is not None]
    precips= [p for p in daily.get('precipitation_sum', []) if p is not None]
    if not temps:
        return None

    # Average temp; total precip divided by number of years (~30)
    avg_temp   = round(sum(temps) / len(temps), 1)
    n_years    = max(1, len(precips) // last_day)
    avg_precip = round(sum(precips) / n_years, 1)

    result = {'temp_c': avg_temp, 'rainfall_mm': avg_precip, 'source': 'open-meteo-climate'}
    with _lock:
        _cache[cache_key] = {'data': result, 'ts': datetime.now()}
    print(f"✅ Open-Meteo climate normals {city} month={month_num}")
    return result


# ── 4. PUBLIC API: monthly weather for N months ───────────────────────────────

def get_monthly_weather(city, month_indices):
    """
    Get weather data for specific months (0-indexed, 0=Jan).
    Strategy per slot:
      - Current calendar month  → live 16-day forecast aggregated
      - Future months (within ~1 yr) → historical archive of same month last year
      - All slots                → fallback: Open-Meteo climate normals
      - Final fallback           → PMD hardcoded averages

    Returns list of dicts: [{month_index, rainfall_mm, temp_c, source}, ...]
    Supports any number of months (6, 12, etc.).
    """
    now      = datetime.now()
    cur_month= now.month - 1   # 0-indexed current month
    forecast = get_forecast_16day(city)
    result   = []

    for i, mi in enumerate(month_indices):
        temp_c      = None
        rainfall_mm = None
        source      = 'fallback'

        # Slot 0 and mi == current calendar month → use live forecast
        if i == 0 and mi == cur_month and forecast and forecast['days']:
            days   = forecast['days']
            temps  = [d['temp_max'] for d in days if d['temp_max'] is not None]
            precips= [d['precip_mm'] or 0 for d in days]
            if temps:
                temp_c      = round(sum(temps) / len(temps), 1)
                # Scale 16-day total to a full 30-day month
                rainfall_mm = round(sum(precips) * (30 / len(precips)), 1)
                source      = 'open-meteo-live'

        # Otherwise try historical archive (same month, prior year)
        if temp_c is None:
            hist = _get_historical_monthly_avg(city, mi)
            if hist:
                temp_c      = hist['temp_c']
                rainfall_mm = hist['rainfall_mm']
                source      = hist['source']

        # Try climate normals as secondary fallback
        if temp_c is None:
            climate = _fetch_climate_normals(city, mi)
            if climate:
                temp_c      = climate['temp_c']
                rainfall_mm = climate['rainfall_mm']
                source      = 'open-meteo-climate'

        # Final PMD fallback
        if temp_c is None:
            temp_c = FALLBACK_TEMP.get(city, FALLBACK_TEMP['Lahore'])[mi]
            source = 'pmd-fallback'
        if rainfall_mm is None:
            rainfall_mm = FALLBACK_RAINFALL.get(city, FALLBACK_RAINFALL['Lahore'])[mi]
            source      = 'pmd-fallback'

        result.append({
            'month_index': mi,
            'rainfall_mm': rainfall_mm,
            'temp_c':      temp_c,
            'source':      source,
        })

    return result


# ── 5. CURRENT WEATHER SUMMARY ────────────────────────────────────────────────

def get_weather_summary(city):
    """
    Get a brief current weather summary for display.
    Returns dict with today's conditions.
    """
    forecast = get_forecast_16day(city)
    if not forecast or not forecast['days']:
        return {'available': False, 'city': city, 'source': 'unavailable'}

    today = forecast['days'][0]
    wcode = today.get('wcode', 0)

    def wcode_desc(c):
        if c == 0:   return '☀️ Clear sky'
        if c <= 3:   return '⛅ Partly cloudy'
        if c <= 9:   return '🌫️ Foggy'
        if c <= 29:  return '🌧️ Rain'
        if c <= 49:  return '🌫️ Fog'
        if c <= 69:  return '🌧️ Rain'
        if c <= 79:  return '❄️ Snow'
        if c <= 84:  return '🌦️ Rain showers'
        if c <= 94:  return '⛈️ Thunderstorm'
        return '⛈️ Heavy thunderstorm'

    return {
        'available':   True,
        'city':        city,
        'temp_max':    today.get('temp_max'),
        'temp_min':    today.get('temp_min'),
        'precip_mm':   today.get('precip_mm', 0),
        'rain_prob':   today.get('rain_prob', 0),
        'description': wcode_desc(wcode),
        'source':      'open-meteo',
        'date':        today.get('date', ''),
    }


# ── 6. FULL YEAR (12-month) WEATHER FOR PLANNING ─────────────────────────────

def get_full_year_weather(city):
    """
    Get weather for all 12 months starting from current month.
    Useful for annual planning charts.
    Returns list of 12 monthly weather dicts.
    """
    now         = datetime.now()
    start_month = now.month - 1  # 0-indexed
    month_idxs  = [(start_month + i) % 12 for i in range(12)]
    return get_monthly_weather(city, month_idxs)
