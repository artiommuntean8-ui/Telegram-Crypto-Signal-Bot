import aiohttp
import matplotlib.pyplot as plt
import io
import logging

logger = logging.getLogger(__name__)

# Setăm backend-ul 'Agg' la nivel de modul pentru execuție headless (server)
plt.switch_backend('Agg')

async def get_binance_data(symbol):
    """Descarcă ultimele 50 de lumânări pentru calcul SMA și RSI."""
    # Endpoint-uri multiple pentru redundanță
    urls = [
        "https://api.binance.com/api/v3/klines",
        "https://api1.binance.com/api/v3/klines",
        "https://api2.binance.com/api/v3/klines",
        "https://api3.binance.com/api/v3/klines"
    ]
    params = {
        "symbol": symbol,
        "interval": "1m",
        "limit": 50 
    }
    
    async with aiohttp.ClientSession() as session:
        blocked_count = 0
        for url in urls:
            try:
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [float(candle[4]) for candle in data]
                    elif response.status == 451:
                        blocked_count += 1
                        logger.warning(f"⚠️ Binance blochează regiunea serverului tău la {url} (Eroare 451).")
                    else:
                        logger.error(f"❌ Endpoint {url} a returnat status {response.status}")
            except Exception as e:
                logger.debug(f"⚠️ Conexiune eșuată la {url}: {e}")
                continue
        
        if blocked_count == len(urls):
            logger.error("🚫 TOATE endpoint-urile Binance sunt blocate. MUTĂ serverul în EUROPA (ex: Frankfurt).")

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

def generate_chart_image(symbol, prices, sma_value):
    """Generează un grafic simplu (Preț vs SMA) și îl returnează ca bytes."""
    plt.figure(figsize=(10, 5))
    
    # Plotăm prețurile (ultimele 50 lumânări)
    plt.plot(prices, label='Price (Close)', color='#1f77b4', linewidth=2)
    
    # Desenăm o linie orizontală pentru SMA curent (orientativ)
    plt.axhline(y=sma_value, color='orange', linestyle='--', label=f'SMA (Trend): {sma_value}')
    
    plt.title(f"Analiza {symbol} - M1 Chart")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Salvăm în memorie (buffer)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf

async def get_market_analysis(symbol, risk_factor):
    """Analizează simbolul dat și returnează semnale cu TP/SL."""
    prices = await get_binance_data(symbol)
    if not prices:
        return {"error": "Acces interzis de Binance (Regiune blocată)."}
    
    current_price = prices[-1]
    rsi, sma = calculate_indicators(prices)
    
    if rsi is None:
        return {"error": "Date insuficiente."}

    # Generăm imaginea graficului
    chart_buf = generate_chart_image(symbol, prices, sma)

    # --- LOGICA DINAMICĂ ---
    signal_type = "NEUTRAL"
    sl = 0.0
    tp1 = 0.0
    tp2 = 0.0
    tp3 = 0.0

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
        "chart": chart_buf,  # Returnăm și imaginea
        "sl": round(sl, 2),
        "tp1": round(tp1, 2),
        "tp2": round(tp2, 2),
        "tp3": round(tp3, 2)
    }