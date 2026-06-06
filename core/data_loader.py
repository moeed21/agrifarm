"""
AgriBazaar — data_loader.py
Reads clean_crop_prices.csv directly. No hardcoded prices.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import threading

_cache = {}
_lock  = threading.Lock()

def _df():
    with _lock:
        if 'df' not in _cache:
            from django.conf import settings
            path = settings.CSV_PATH
            if not Path(path).exists():
                raise FileNotFoundError(
                    f"Dataset not found: {path}\n"
                    f"Place clean_crop_prices.csv in your project root folder."
                )
            print(f"[AgriBazaar] Loading {path}...")
            df = pd.read_csv(path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            print(f"[AgriBazaar] {len(df):,} rows | {df['date'].min().date()} -> {df['date'].max().date()}")
            _cache['df'] = df
        return _cache['df']

def get_crops():    return sorted(_df()['crop'].unique().tolist())
def get_cities():   return sorted(_df()['city'].unique().tolist())
def get_markets():  return sorted(_df()['market_name'].unique().tolist())

def get_dataset_info():
    df = _df()
    return {
        'rows':      len(df),
        'crops':     get_crops(),
        'cities':    get_cities(),
        'markets':   get_markets(),
        'date_from': str(df['date'].min().date()),
        'date_to':   str(df['date'].max().date()),
    }

def get_monthly_avg(crop, city):
    df  = _df()
    sub = df[(df['crop'] == crop) & (df['city'] == city)]
    if sub.empty:
        return [0] * 12
    avg = sub['avg_price'].mean()
    m   = sub.groupby('month')['avg_price'].mean()
    return [int(round(float(m.get(i, avg)))) for i in range(1, 13)]

def get_seasonal_indices(crop):
    df  = _df()
    sub = df[df['crop'] == crop]
    if sub.empty:
        return [1.0] * 12
    avg = sub['avg_price'].mean()
    m   = sub.groupby('month')['avg_price'].mean()
    return [round(float(m.get(i, avg)) / avg, 3) for i in range(1, 13)]

def get_all_city_prices(crop):
    df  = _df()
    sub = df[df['crop'] == crop].sort_values('date')
    if sub.empty:
        return []
    latest = sub.groupby(['city', 'market_name']).last().reset_index()
    summary = latest.groupby('city').agg(
        avg_price=('avg_price','mean'),
        min_price=('min_price','min'),
        max_price=('max_price','max'),
    ).reset_index()
    result = []
    for _, row in summary.sort_values('avg_price').iterrows():
        result.append({
            'city':      row['city'],
            'avg_price': int(round(row['avg_price'])),
            'min_price': int(row['min_price']),
            'max_price': int(row['max_price']),
        })
    return result

def get_latest_mandi_prices(city, crop):
    df  = _df()
    sub = df[(df['crop'] == crop) & (df['city'] == city)].sort_values('date')
    if sub.empty:
        return []
    latest  = sub.groupby('market_name').last().reset_index()
    cutoff  = sub['date'].max() - timedelta(days=7)
    week_ago= sub[sub['date'] <= cutoff].groupby('market_name').last().reset_index()
    week_ago= week_ago[['market_name','avg_price']].rename(columns={'avg_price':'p7'})
    latest  = latest.merge(week_ago, on='market_name', how='left')
    latest['chg'] = ((latest['avg_price'] - latest['p7']) / latest['p7'] * 100).round(1)
    result = []
    for _, r in latest.sort_values('avg_price').iterrows():
        result.append({
            'market':    r['market_name'],
            'city':      city,
            'crop':      crop,
            'price':     int(r['avg_price']),
            'min_price': int(r['min_price']),
            'max_price': int(r['max_price']),
            'volatility':round(float(r.get('volatility', 0)), 1),
            'change_7d': round(float(r['chg']), 1) if not pd.isna(r['chg']) else 0,
            'date':      str(r['date'].date()),
            'days_old':  (datetime.now() - r['date']).days,
        })
    return result

def get_market_listings():
    df     = _df()
    latest = df.sort_values('date').groupby(['city','crop','market_name']).last().reset_index()
    out    = []
    lid    = 1
    for city in sorted(df['city'].unique()):
        for crop in sorted(df['crop'].unique()):
            rows = latest[(latest['city']==city)&(latest['crop']==crop)].sort_values('avg_price')
            if rows.empty:
                continue
            r = rows.iloc[0]
            out.append({
                'id':        lid,
                'crop':      crop,
                'city':      city,
                'market':    r['market_name'],
                'price':     int(r['avg_price']),
                'min_price': int(r['min_price']),
                'max_price': int(r['max_price']),
                'qty':       500,
                'date':      str(r['date'].date()),
                'seller':    f"{r['market_name']} Traders",
                'phone':     f"03{abs(hash(city))%100:02d}-{abs(hash(crop))%10000000:07d}",
                'sid':       f"s{lid}",
                'status':    'active',
                'desc':      f"Fresh {crop} from {r['market_name']}, {city}. Direct from source.",
                'change_7d': 0,
            })
            lid += 1
    return out

def get_price_history(crop, city, days=90):
    df     = _df()
    cutoff = df['date'].max() - timedelta(days=days)
    sub    = df[(df['crop']==crop)&(df['city']==city)&(df['date']>=cutoff)].sort_values('date')
    if sub.empty:
        return []
    daily = sub.groupby('date').agg(avg=('avg_price','mean'),min=('min_price','min'),max=('max_price','max')).reset_index()
    return [{'date':str(r['date'].date()),'avg':int(round(r['avg'])),'min':int(r['min']),'max':int(r['max'])} for _,r in daily.iterrows()]
