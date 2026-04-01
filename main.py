# main.py
import sys
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BufferedInputFile
from config import BOT_TOKEN, PAIRS_CONFIG
from database import init_db, get_active_users, extend_subscription
from handlers import router
from market_data import get_market_analysis, is_market_open

# Configurare logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def market_scanner(bot: Bot):
    """Rulează în fundal și caută semnale."""
    logger.info(f"📡 Scanner pornit pentru {len(PAIRS_CONFIG)} perechi...")
    
    # Ținem minte ultimul semnal ca să nu spamăm
    last_signal_types = {pair: None for pair in PAIRS_CONFIG}
    
    while True:
        if not is_market_open():
            # Dacă piața e închisă, așteptăm un minut și verificăm din nou
            await asyncio.sleep(60)
            continue
            
        # Twelve Data Free are o limită de 800 de cereri pe zi.
        # Pentru a rula 24/7 (23h de piață deschisă), trebuie să așteptăm ~110 secunde.
        # 82.800 secunde (23h) / 800 cereri = 103.5 secunde/cerere.
        # Folosim 110 secunde pentru a fi în siguranță.
        await asyncio.sleep(110)  
        
        for symbol, settings in PAIRS_CONFIG.items():
            try:
                # 1. Luăm datele reale cu factorul de risc specific
                analysis = await get_market_analysis(symbol, settings['risk'])
                
                if "error" in analysis:
                    logger.warning(f"⚠️ {settings['name']} ({symbol}): {analysis['error']}")
                    continue
                
                signal_action = None
                verdict = analysis['signal']

                # Log periodic (Acum va apărea mereu în terminal la fiecare 10 secunde)
                logger.info(f"📊 {settings['name']} | Preț: {analysis['price']} | RSI: {analysis['rsi']} | Verdict: {verdict}")
                
                # 2. Verificăm semnalul (CU filtru anti-spam)
                if verdict == "Buy" and last_signal_types[symbol] != "Buy":
                    signal_action = verdict
                    last_signal_types[symbol] = "Buy"
                elif verdict == "Sell" and last_signal_types[symbol] != "Sell":
                    signal_action = verdict
                    last_signal_types[symbol] = "Sell"
                
                # Dacă nu e semnal de acțiune (e Neutral), nu trimitem pe Telegram
                if not signal_action:
                    continue

                # 3. Construim mesajul
                message = (
                    f"🏆 **{settings['name']}**\n"
                    f"Signal: **{signal_action}** 🟢🔴\n"
                    f"Entry price: `{analysis['price']}`\n\n"
                    f"🎯 **TP 1:** `{analysis['tp1']}`\n"
                    f"🎯 **TP 2:** `{analysis['tp2']}`\n"
                    f"🎯 **TP 3:** `{analysis['tp3']}`\n\n"
                    f"🛡️ **SL:** `{analysis['sl']}`"
                )
                
                # 4. Trimitem la toți userii activi
                users = await get_active_users()
                if users:
                    logger.info(f"Semnal {settings['name']} -> {len(users)} useri.")
                    for user_id in users:
                        # Resetăm cursorul imaginii pentru fiecare trimitere
                        analysis['chart'].seek(0)
                        photo_file = BufferedInputFile(analysis['chart'].read(), filename="chart.png")
                        try:
                            await bot.send_photo(user_id, photo=photo_file, caption=message, parse_mode="Markdown")
                        except Exception as e:
                            logger.error(f"Eroare trimitere la {user_id}: {e}")
            
            except Exception as e:
                logger.error(f"Eroare scanner pentru {symbol}: {e}")

async def main():
    # 1. Inițializare baza de date
    await init_db()

    # Verificare critică pentru Token
    if not BOT_TOKEN:
        logger.error("❌ EROARE: BOT_TOKEN lipsește! Verifică dacă ai creat fișierul '.env' cu token-ul tău.")
        sys.exit(1)
    
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
