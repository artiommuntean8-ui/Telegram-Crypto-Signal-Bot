import aiohttp

async def get_binance_data():
    """Descarcă ultimele 50 de lumânări pentru calcul SMA și RSI."""
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": "PAXGUSDT",  # Folosim PAX Gold ca proxy pentru XAUUSD
        "interval": "1m",
        "limit": 50 
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return [float(candle[4]) for candle in data] # Close prices
            return []

def calculate_indicators(prices):
    """Calculează RSI și SMA (Simple Moving Average)."""
    if len(prices) < 15:
        return None, None

    # 1. Calcul RSI (14 perioade)
    period = 14
    gains, losses = [], []
    for i in range(1, period + 1):
        change = prices[-period + i - 1] - prices[-period + i - 2]
        if change > 0: gains.append(change); losses.append(0)
        else: gains.append(0); losses.append(abs(change))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0: rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    # 2. Calcul SMA (Media pe ultimele 20 perioade)
    sma = sum(prices[-20:]) / 20
    
    return round(rsi, 2), round(sma, 2)

async def get_market_analysis():
    """Analizează XAUUSD și returnează semnale cu TP/SL."""
    prices = await get_binance_data()
    if not prices:
        return {"error": "Conexiune XAUUSD eșuată."}
    
    current_price = prices[-1]
    rsi, sma = calculate_indicators(prices)
    
    if rsi is None:
        return {"error": "Date insuficiente."}

    # --- LOGICA XAUUSD (GOLD) ---
    signal_type = "NEUTRAL"
    sl = 0.0
    tp1 = 0.0
    tp2 = 0.0
    tp3 = 0.0

    # Setări distanță (ajustate pentru scalping pe Aur)
    # SL aprox 3$ | TP1 2$ | TP2 5$ | TP3 9$
    risk_factor = 0.0015  # 0.15% mișcare pentru SL

    if rsi < 30:
        signal_type = "Buy"
        sl = current_price - (current_price * risk_factor)
        tp1 = current_price + (current_price * 0.0010) # Safe
        tp2 = current_price + (current_price * 0.0025) # Risk Active
        tp3 = current_price + (current_price * 0.0045) # Big Risk
    elif rsi > 70:
        signal_type = "Sell"
        sl = current_price + (current_price * risk_factor)
        tp1 = current_price - (current_price * 0.0010)
        tp2 = current_price - (current_price * 0.0025)
        tp3 = current_price - (current_price * 0.0045)

    return {
        "price": current_price,
        "rsi": rsi,
        "sma": sma,
        "signal": signal_type,
        "sl": round(sl, 2),
        "tp1": round(tp1, 2),
        "tp2": round(tp2, 2),
        "tp3": round(tp3, 2)
    }