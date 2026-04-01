import yfinance as yf
import asyncio
import matplotlib.pyplot as plt
import io
import logging
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

# Setăm backend-ul 'Agg' la nivel de modul pentru execuție headless (server)
plt.switch_backend('Agg')

def is_market_open():
    """Verifică dacă piața XAUUSD este deschisă."""
    now = datetime.now()
    # Sâmbătă (5) și Duminică (6) piața este închisă
    if now.weekday() >= 5:
        return False
    # Pauza zilnică între 23:00 și 00:00
    if now.hour == 23:
        return False
    return True

async def get_binance_data(symbol):
    """Descarcă datele XAUUSD folosind Yahoo Finance (ocolind blocajele Binance)."""
    # GC=F (Gold Futures) este mai precis pentru prețul aurului real (XAUUSD) pe Yahoo Finance
    ticker_symbol = "GC=F" if symbol == "XAUUSD" else symbol
    
    try:
        # yfinance este o bibliotecă sincronă, o rulăm în thread-ul separat pentru a nu bloca botul
        df = await asyncio.to_thread(yf.download, tickers=ticker_symbol, period="1d", interval="1m", progress=False, auto_adjust=True)
        
        if df.empty:
            logger.warning(f"⚠️ Nu am primit date pentru {ticker_symbol}")
            return []

        # Verificăm ora ultimei lumânări pentru a detecta delay-ul
        last_candle_time = df.index[-1].to_pydatetime()
        now = datetime.now(last_candle_time.tzinfo)
        delay_minutes = int((now - last_candle_time).total_seconds() / 60)
        
        logger.info(f"✅ {symbol} | Preț: {df['Close'].iloc[-1]:.2f} | Delay: {delay_minutes} min | Ora Date: {last_candle_time.strftime('%H:%M:%S')}")
        
        if delay_minutes > 5:
            logger.warning(f"⚠️ Atenție: Datele pentru {symbol} au o întârziere de {delay_minutes} minute!")

        # Extragerea prețurilor și asigurarea formatului corect
        close_prices = df['Close'].values.flatten().tolist()
        return [round(float(p), 2) for p in close_prices]

    except Exception as e:
        logger.error(f"❌ Eroare la preluarea datelor Yahoo Finance: {e}")
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
        return {"error": "Nu s-au putut prelua datele de la furnizorul de piață."}
    
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