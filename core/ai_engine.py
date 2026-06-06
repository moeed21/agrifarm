"""
AgriBazaar — ai_engine.py
AI analysis + 6-month farmer forecast.
Prices: from CSV via data_loader
Weather: from Open-Meteo API via weather.py (falls back to PMD climatology)
"""
from datetime import datetime
from . import data_loader as dl
from . import weather     as wx
try:
    from . import prophet_engine as pe
    _PROPHET_AVAILABLE = pe.is_available()   # Holt-Winters via statsmodels
except Exception:
    pe = None
    _PROPHET_AVAILABLE = False

MONTH_NAMES = ['January','February','March','April','May','June',
               'July','August','September','October','November','December']
MONTH_SHORT = ['Jan','Feb','Mar','Apr','May','Jun',
               'Jul','Aug','Sep','Oct','Nov','Dec']

CROP_OPTIMA = {
    # Vegetables
    'Tomato':      {'tempMin':18,'tempMax':29,'rainMin':20,'rainMax':80},
    'Potato':      {'tempMin':15,'tempMax':25,'rainMin':30,'rainMax':100},
    'Onion':       {'tempMin':13,'tempMax':28,'rainMin':15,'rainMax':70},
    'Garlic':      {'tempMin':10,'tempMax':25,'rainMin':15,'rainMax':60},
    'Carrot':      {'tempMin':12,'tempMax':24,'rainMin':25,'rainMax':80},
    'Peas':        {'tempMin':10,'tempMax':22,'rainMin':30,'rainMax':90},
    'Cucumber':    {'tempMin':20,'tempMax':32,'rainMin':30,'rainMax':90},
    'Brinjal':     {'tempMin':22,'tempMax':35,'rainMin':25,'rainMax':85},
    'Spinach':     {'tempMin':10,'tempMax':24,'rainMin':20,'rainMax':70},
    'Cauliflower': {'tempMin':15,'tempMax':25,'rainMin':25,'rainMax':80},
    'Cabbage':     {'tempMin':15,'tempMax':25,'rainMin':25,'rainMax':80},
    'Bitter Gourd':{'tempMin':25,'tempMax':38,'rainMin':30,'rainMax':90},
    'Bottle Gourd':{'tempMin':25,'tempMax':38,'rainMin':30,'rainMax':90},
    'Tinda':       {'tempMin':25,'tempMax':38,'rainMin':25,'rainMax':85},
    'Ladyfinger':  {'tempMin':25,'tempMax':40,'rainMin':25,'rainMax':85},
    'Turnip':      {'tempMin':10,'tempMax':22,'rainMin':20,'rainMax':70},
    'Radish':      {'tempMin':10,'tempMax':22,'rainMin':20,'rainMax':65},
    'Beetroot':    {'tempMin':10,'tempMax':24,'rainMin':20,'rainMax':70},
    'Corn':        {'tempMin':18,'tempMax':35,'rainMin':40,'rainMax':120},
    'Ginger':      {'tempMin':20,'tempMax':32,'rainMin':60,'rainMax':150},
    'Turmeric':    {'tempMin':20,'tempMax':35,'rainMin':60,'rainMax':150},
    # Fruits
    'Mango':       {'tempMin':24,'tempMax':42,'rainMin':20,'rainMax':100},
    'Banana':      {'tempMin':20,'tempMax':38,'rainMin':60,'rainMax':200},
    'Apple':       {'tempMin':5, 'tempMax':22,'rainMin':40,'rainMax':100},
    'Orange':      {'tempMin':15,'tempMax':35,'rainMin':30,'rainMax':100},
    'Guava':       {'tempMin':20,'tempMax':38,'rainMin':30,'rainMax':100},
    'Watermelon':  {'tempMin':24,'tempMax':40,'rainMin':15,'rainMax':80},
    'Melon':       {'tempMin':22,'tempMax':38,'rainMin':15,'rainMax':80},
    'Grapes':      {'tempMin':15,'tempMax':35,'rainMin':20,'rainMax':80},
    'Lemon':       {'tempMin':15,'tempMax':38,'rainMin':20,'rainMax':100},
    'Pomegranate': {'tempMin':18,'tempMax':38,'rainMin':15,'rainMax':80},
    'Peach':       {'tempMin':10,'tempMax':30,'rainMin':30,'rainMax':90},
    'Apricot':     {'tempMin':5, 'tempMax':28,'rainMin':20,'rainMax':80},
    'Strawberry':  {'tempMin':10,'tempMax':22,'rainMin':30,'rainMax':80},
    # Grains & Pulses
    'Wheat':       {'tempMin':12,'tempMax':25,'rainMin':20,'rainMax':80},
    'Rice':        {'tempMin':22,'tempMax':38,'rainMin':80,'rainMax':250},
    'Maize':       {'tempMin':18,'tempMax':35,'rainMin':40,'rainMax':120},
    'Chickpeas':   {'tempMin':10,'tempMax':28,'rainMin':15,'rainMax':60},
    'Lentils':     {'tempMin':10,'tempMax':25,'rainMin':15,'rainMax':60},
    'Moong Dal':   {'tempMin':20,'tempMax':38,'rainMin':20,'rainMax':80},
    'Masoor Dal':  {'tempMin':10,'tempMax':25,'rainMin':15,'rainMax':65},
    # Cash Crops
    'Sugarcane':   {'tempMin':20,'tempMax':38,'rainMin':80,'rainMax':200},
    'Cotton':      {'tempMin':25,'tempMax':42,'rainMin':25,'rainMax':100},
    'Sunflower':   {'tempMin':18,'tempMax':35,'rainMin':25,'rainMax':90},
}

def _wsi(temp, rain, crop):
    o = CROP_OPTIMA.get(crop, {'tempMin':15,'tempMax':30,'rainMin':20,'rainMax':80})
    ts = min(50,(o['tempMin']-temp)*4) if temp<o['tempMin'] else min(50,(temp-o['tempMax'])*3) if temp>o['tempMax'] else 0
    rs = min(50,(o['rainMin']-rain)*.8) if rain<o['rainMin'] else min(50,(rain-o['rainMax'])*.25) if rain>o['rainMax'] else 0
    return min(100, round(ts+rs))

def _rain_label(mm):
    if mm>=200: return {'label':'🌊 Flood Risk',  'cls':'flood',   'color':'#1a3a8f','bg':'#dbeafe'}
    if mm>=100: return {'label':'⛈️ Heavy Rain',  'cls':'heavy',   'color':'#1e40af','bg':'#eff6ff'}
    if mm>=40:  return {'label':'🌧️ Moderate',    'cls':'moderate','color':'#0369a1','bg':'#f0f9ff'}
    if mm>=15:  return {'label':'🌦️ Light Rain',  'cls':'light',   'color':'#0891b2','bg':'#ecfeff'}
    if mm>=5:   return {'label':'☀️ Mostly Dry',  'cls':'dry',     'color':'#ca8a04','bg':'#fefce8'}
    return             {'label':'🌵 Drought Risk','cls':'drought', 'color':'#b45309','bg':'#fff7ed'}

def _temp_label(c):
    if c>=42: return {'label':'🔥 Extreme Heat','color':'#dc2626'}
    if c>=38: return {'label':'☀️ Very Hot',    'color':'#ea580c'}
    if c>=30: return {'label':'🌤️ Warm',        'color':'#ca8a04'}
    if c>=20: return {'label':'🌿 Mild',        'color':'#16a34a'}
    if c>=10: return {'label':'🍂 Cool',        'color':'#0891b2'}
    return           {'label':'❄️ Cold',         'color':'#1d4ed8'}

def _mult(wsi):
    if wsi>=70: return 1.25
    if wsi>=50: return 1.15
    if wsi>=35: return 1.08
    if wsi>=20: return 1.00
    return 0.95


def analyze(crop, city, role='seller'):
    """
    Core AI analysis for a crop+city.
    Prices from CSV. Weather used for signal context.
    """
    m       = datetime.now().month - 1
    monthly = dl.get_monthly_avg(crop, city)
    cur,prev,nxt = monthly[m], monthly[(m-1)%12], monthly[(m+1)%12]
    m30  = round((cur-prev)/prev*100,1) if prev else 0
    nxtC = round((nxt-cur)/cur*100,1)  if cur  else 0
    best_m  = monthly.index(max(monthly))
    worst_m = monthly.index(min(monthly))
    all_cities = dl.get_all_city_prices(crop)
    cheapest = all_cities[0]  if all_cities else {'city':city,'avg_price':cur}
    priciest = all_cities[-1] if all_cities else {'city':city,'avg_price':cur}

    # Get current weather — try fast wttr.in first, fall back to Open-Meteo
    weather_now = wx.get_current_weather_fast(city) or wx.get_weather_summary(city)

    sigs = []
    if m30>8:    sigs.append({'dot':'red',  'lbl':'Strong Upward Momentum','det':f'+{m30}% vs last month','score': 1 if role=='seller' else -1})
    elif m30>3:  sigs.append({'dot':'amber','lbl':'Mild Upward Trend',      'det':f'+{m30}% this month',  'score':.5 if role=='seller' else -.5})
    elif m30<-8: sigs.append({'dot':'green','lbl':'Sharp Price Decline',    'det':f'{m30}% — buy window', 'score':-1 if role=='seller' else 1})
    elif m30<-3: sigs.append({'dot':'amber','lbl':'Mild Downward Pressure', 'det':f'{m30}% this month',   'score':-.5})
    else:        sigs.append({'dot':'blue', 'lbl':'Stable Market',          'det':f'±{abs(m30)}% — steady','score':0})

    if m==best_m:
        sigs.append({'dot':'green' if role=='seller' else 'red',
                     'lbl':f'Peak Season ({MONTH_SHORT[best_m]})',
                     'det':'Historically highest price now','score':1 if role=='seller' else -1})
    elif m==worst_m:
        sigs.append({'dot':'red' if role=='seller' else 'green',
                     'lbl':f'Harvest Low ({MONTH_SHORT[worst_m]})',
                     'det':'Historically lowest price now','score':-1 if role=='seller' else 1})

    if nxtC>8:    sigs.append({'dot':'green' if role=='seller' else 'red', 'lbl':f'Next Month: +{nxtC}%','det':f'{MONTH_SHORT[(m+1)%12]} forecast higher','score':.8})
    elif nxtC<-8: sigs.append({'dot':'red' if role=='seller' else 'green', 'lbl':f'Next Month: {nxtC}%', 'det':f'{MONTH_SHORT[(m+1)%12]} forecast lower', 'score':-.8})

    # Live weather signal
    if weather_now['available']:
        rain = weather_now.get('precip_mm', 0) or 0
        temp = weather_now.get('temp_max', 30) or 30
        desc = weather_now.get('description', '')
        if rain > 20:
            sigs.append({'dot':'amber','lbl':f'Live Weather: {desc}','det':f'{rain}mm today — transport may be affected','score':-.3})
        elif temp > 40:
            sigs.append({'dot':'red','lbl':f'Live Weather: {desc}','det':f'{temp}°C today — heat stress on crops','score':-.2})
        else:
            sigs.append({'dot':'blue','lbl':f'Live Weather: {desc}','det':f'{temp}°C · {rain}mm · Open-Meteo','score':0})
    else:
        # Fallback weather info from climatology
        fb_rain = wx.FALLBACK_RAINFALL.get(city, wx.FALLBACK_RAINFALL['Lahore'])[m]
        fb_temp = wx.FALLBACK_TEMP.get(city, wx.FALLBACK_TEMP['Lahore'])[m]
        sigs.append({'dot':'blue','lbl':'Weather (PMD climate avg)','det':f'~{fb_temp}°C · ~{fb_rain}mm this month','score':0})

    try:
        info = dl.get_dataset_info()
        sigs.append({'dot':'blue','lbl':f"CSV: {info['rows']:,} mandi records",'det':f"{info['date_from']} → {info['date_to']}",'score':0})
    except: pass

    raw  = sum(s['score'] for s in sigs)/len(sigs)
    conf = min(97,max(45,round(58+raw*22)))

    if role=='seller':
        if raw>.4:   v,vc,vi,vr = 'GOOD TIME TO SELL','buy','✅',f'Market favours selling {crop} in {city} now.'
        elif raw<-.3:v,vc,vi,vr = 'HOLD — WAIT FOR BETTER PRICE','wait','⏳','Unfavourable. Holding may yield better returns.'
        else:        v,vc,vi,vr = 'NEUTRAL — STANDARD CONDITIONS','wait','⚖️','Mixed signals. Standard selling conditions apply.'
    else:
        if raw>.3:   v,vc,vi,vr = 'GOOD TIME TO BUY','buy','🛒',f'Buying conditions favourable for {crop} in {city}.'
        elif raw<-.4:v,vc,vi,vr = 'AVOID — PRICES TOO HIGH','avoid','🚫',f'Prices elevated. Consider {cheapest["city"]}.'
        else:        v,vc,vi,vr = 'WAIT — BETTER PRICE COMING','wait','⏳',f'Prices may improve in {MONTH_NAMES[(m+1)%12]}.'

    return {
        'crop':crop,'city':city,'role':role,
        'cur':cur,'prev':prev,'nxt':nxt,
        'm30':m30,'nxtC':nxtC,'conf':conf,
        'verdict':v,'vc':vc,'vi':vi,'vr':vr,
        'sigs':sigs,'monthly':monthly,
        'best_month':MONTH_NAMES[best_m],
        'worst_month':MONTH_NAMES[worst_m],
        'all_cities':all_cities,'cheapest':cheapest,'priciest':priciest,
        'weather_now':weather_now,
    }


def farmer_forecast(crop, city, start_month):
    """
    6-month forward forecast.
    Prices: Prophet model (learned from CSV) with WSI weather adjustment on top.
    Falls back to historical monthly averages if Prophet is unavailable.
    """
    monthly     = dl.get_monthly_avg(crop, city)   # fallback averages
    month_idxs  = [(start_month + i) % 12 for i in range(6)]

    # ── Fetch Prophet predictions ───────────────────────────────────────────
    prophet_data = None
    if _PROPHET_AVAILABLE and pe is not None:
        try:
            prophet_data = pe.get_6month_forecast(crop, city, start_month)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(f'[Prophet] Forecast error: {exc}')

    # ── Fetch weather for all 6 months ──────────────────────────────────────
    weather_data = wx.get_monthly_weather(city, month_idxs)

    months_out = []
    for i, w in enumerate(weather_data):
        mi    = w['month_index']
        rain  = w['rainfall_mm']
        temp  = w['temp_c']
        wsrc  = w['source']

        wsi = _wsi(temp, rain, crop)

        # ── Choose base price ────────────────────────────────────────────────
        if prophet_data and i < len(prophet_data):
            pd_row        = prophet_data[i]
            base_price    = pd_row['prophet_price']
            prophet_upper = pd_row['prophet_upper']
            prophet_lower = pd_row['prophet_lower']
            conf_pct      = pd_row['confidence_pct']
            using_prophet = True
            engine_name   = pd_row.get('engine', 'prophet')
        else:
            base_price    = monthly[mi]          # fallback: historical avg
            prophet_upper = int(base_price * 1.10)
            prophet_lower = int(base_price * 0.90)
            conf_pct      = 55
            using_prophet = False
            engine_name   = 'historical'

        # ── Apply WSI weather multiplier on top of Prophet base ──────────────
        adj   = int(round(base_price * _mult(wsi)))
        flood = rain >= 150 and city in ['Lahore','Faislabad','Sialkot','Rawalpindi','Islamabad']
        drought = rain < 10 and temp > 35

        alerts = []
        if flood:    alerts.append({'type':'danger', 'icon':'🌊','msg':f'Flood risk in {MONTH_NAMES[mi]} — supply disruption, prices may spike'})
        if drought:  alerts.append({'type':'danger', 'icon':'🌵','msg':'Drought risk — poor yields, prices likely to rise'})
        if temp>=42: alerts.append({'type':'warning','icon':'🔥','msg':f'Extreme heat ({temp}°C) — heat stress will reduce {crop} yield'})
        if temp<=8:  alerts.append({'type':'info',   'icon':'❄️','msg':f'Cold weather ({temp}°C) — frost risk for {crop}'})
        if rain>=200:alerts.append({'type':'danger', 'icon':'⛈️','msg':f'Very heavy rain ({rain}mm) — mandi road closures possible'})
        if wsi<=15:  alerts.append({'type':'success','icon':'✅','msg':'Ideal growing conditions — good harvest expected'})

        # Scaled confidence bands for the adjusted price
        adj_upper = int(round(prophet_upper * _mult(wsi)))
        adj_lower = int(round(prophet_lower * _mult(wsi)))

        months_out.append({
            'month_index'   : mi,
            'month_name'    : MONTH_NAMES[mi],
            'month_short'   : MONTH_SHORT[mi],
            'base_price'    : monthly[mi],          # always the raw historical avg
            'adjusted_price': adj,                  # Prophet (or hist) × WSI mult
            'prophet_price' : base_price,
            'prophet_upper' : prophet_upper,
            'prophet_lower' : prophet_lower,
            'adj_upper'     : adj_upper,
            'adj_lower'     : adj_lower,
            'confidence_pct': conf_pct,
            'using_prophet' : using_prophet,
            'engine'        : engine_name,
            'rainfall_mm'   : rain,
            'temp_c'        : temp,
            'wsi'           : wsi,
            'rain_label'    : _rain_label(rain),
            'temp_label'    : _temp_label(temp),
            'flood_risk'    : flood,
            'drought_risk'  : drought,
            'alerts'        : alerts,
            'weather_source': wsrc,
            'sell_score'    : round(adj/10 + (100-wsi)/5, 1),
        })

    best  = max(months_out, key=lambda m: m['sell_score'])
    avoid = [m for m in months_out if m['flood_risk'] or m['wsi'] >= 60]
    avg_wsi = round(sum(m['wsi'] for m in months_out) / 6)
    risk = ('HIGH'   if avg_wsi >= 50 or sum(1 for m in months_out if m['flood_risk']) >= 2
            else 'MEDIUM' if avg_wsi >= 30
            else 'LOW')

    # City comparison using live weather for each city
    city_cmp = []
    for c in dl.get_cities():
        cm        = dl.get_monthly_avg(crop, c)
        c_weather = wx.get_monthly_weather(c, month_idxs)
        ap = round(sum(cm[w['month_index']] for w in c_weather) / 6)
        aw = round(sum(_wsi(w['temp_c'], w['rainfall_mm'], crop) for w in c_weather) / 6)
        city_cmp.append({'city':c, 'avg_price':ap, 'avg_wsi':aw, 'score':round(ap - aw*0.5, 1)})
    city_cmp.sort(key=lambda x: -x['score'])

    sources_used = list(set(m['weather_source'] for m in months_out))
    if 'open-meteo-live' in sources_used or 'open-meteo-climate' in sources_used:
        weather_src = '🌐 Open-Meteo (live)'
    else:
        weather_src = '📊 Pakistan Met Dept (climatology)'

    using_prophet_any = any(m['using_prophet'] for m in months_out)
    # Determine which engine actually ran
    engines_used = set(m.get('engine', 'historical') for m in months_out)
    if 'prophet' in engines_used:
        forecast_engine = 'prophet'
    elif 'holtwinters' in engines_used:
        forecast_engine = 'holtwinters'
    else:
        forecast_engine = 'historical'

    return {
        'crop'           : crop,
        'city'           : city,
        'months'         : months_out,
        'best_month'     : best,
        'avoid_months'   : avoid,
        'overall_risk'   : risk,
        'avg_wsi'        : avg_wsi,
        'city_comparison': city_cmp,
        'best_city'      : city_cmp[0] if city_cmp else None,
        'weather_source' : weather_src,
        'using_prophet'  : using_prophet_any,
        'forecast_engine': forecast_engine,
    }


def ai_badge(price, crop, city):
    m   = datetime.now().month - 1
    avg = dl.get_monthly_avg(crop, city)[m]
    if not avg: return {'cls':'badge-fair','txt':'🤖 Fair Price'}
    r = price / avg
    if r < .92: return {'cls':'badge-below','txt':'🤖 Below Average'}
    if r > 1.12:return {'cls':'badge-above','txt':'🤖 Above Average'}
    return              {'cls':'badge-fair', 'txt':'🤖 Fair Price'}
