import aiohttp

async def get_binance_data():
    """Descarcă ultimele 50 de lumânări pentru calcul SMA și RSI."""
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
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
    """Analizează piața și returnează verdictul."""
    prices = await get_binance_data()
    if not prices:
        return {"error": "Nu pot conecta la Binance."}
    
    current_price = prices[-1]
    rsi, sma = calculate_indicators(prices)
    
    if rsi is None:
        return {"error": "Date insuficiente."}

    # Logica avansată LONG/SHORT
    signal = "NEUTRAL (Așteaptă) ⚪"
    if rsi < 30:
        signal = "LONG (Cumpără) 🟢" if current_price > sma else "LONG RISCANT (Trend Scădere) ⚠️"
    elif rsi > 70:
        signal = "SHORT (Vinde) 🔴" if current_price < sma else "SHORT RISCANT (Trend Creștere) ⚠️"

    return {
        "price": current_price,
        "rsi": rsi,
        "sma": sma,
        "signal": signal
    }