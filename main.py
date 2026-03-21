# main.py
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db, get_active_users
from handlers import router

# Configurare logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MARKET DATA & INDICATORS (Real Logic) ---
async def get_binance_price():
    """Descarcă ultimele 15 lumânări (candles) de pe Binance."""
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": "1m", # Interval de 1 minut pentru teste rapide
        "limit": 15       # Avem nevoie de 14 perioade pentru RSI
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                # Returnăm doar prețurile de închidere (Close Price este indexul 4)
                return [float(candle[4]) for candle in data]
            return []

def calculate_rsi(prices, period=14):
    """Calculează RSI (Relative Strength Index) matematic."""
    if len(prices) < period + 1:
        return 50.0 # Nu avem destule date

    gains = []
    losses = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

async def market_scanner(bot: Bot):
    """Rulează în fundal și caută semnale."""
    logger.info("📡 Scanner-ul REAL Binance a pornit...")
    
    # Ținem minte ultimul semnal ca să nu spamăm
    last_signal_type = None 
    
    while True:
        await asyncio.sleep(10)  # Verificăm piața la fiecare 10 secunde
        
        try:
            # 1. Luăm datele reale
            prices = await get_binance_price()
            if not prices:
                continue

            current_price = prices[-1]
            rsi = calculate_rsi(prices)
            
            signal_action = None
            
            # 2. Logica de Trading (Strategia RSI)
            if rsi < 30 and last_signal_type != "BUY":
                signal_action = "LONG (Cumpără) 🟢"
                last_signal_type = "BUY"
            elif rsi > 70 and last_signal_type != "SELL":
                signal_action = "SHORT (Vinde) 🔴"
                last_signal_type = "SELL"
            
            # Dacă nu e semnal, doar afișăm în consolă statusul
            if not signal_action:
                logger.info(f"Monitorizare: BTC={current_price}$ | RSI={rsi}")
                continue

            # 3. Construim mesajul
            message = (
                f"🚨 **SEMNAL TRADING REAL**\n\n"
                f"💎 **Simbol:** `BTC/USDT`\n"
                f"⚡ **Acțiune:** {signal_action}\n"
                f"💵 **Preț:** {current_price}$\n"
                f"📊 **Indicator:** RSI este {rsi}\n"
            )
            
            # 4. Trimitem la toți userii activi
            users = await get_active_users()
            if users:
                logger.info(f"Trimit semnal la {len(users)} utilizatori.")
                for user_id in users:
                    try:
                        await bot.send_message(user_id, message, parse_mode="Markdown")
                    except Exception as e:
                        logger.error(f"Eroare trimitere la {user_id}: {e}")
        
        except Exception as e:
            logger.error(f"Eroare în scanner: {e}")

async def main():
    # 1. Inițializare baza de date
    await init_db()
    
    # 2. Configurare Bot și Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # 3. Înregistrare routere (handlers)
    dp.include_router(router)
    
    # 4. Pornire scanner în background
    asyncio.create_task(market_scanner(bot))
    
    # 5. Start bot polling
    logger.info("Botul a pornit! 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot oprit manual.")
