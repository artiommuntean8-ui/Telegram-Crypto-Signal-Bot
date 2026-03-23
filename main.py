# main.py
import sys
import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db, get_active_users
from handlers import router
from market_data import get_market_analysis

# Configurare logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def market_scanner(bot: Bot):
    """Rulează în fundal și caută semnale."""
    logger.info("📡 Scanner-ul XAUUSD (Gold) a pornit...")
    
    # Ținem minte ultimul semnal ca să nu spamăm
    last_signal_type = None 
    
    while True:
        await asyncio.sleep(10)  # Verificăm piața la fiecare 10 secunde
        
        try:
            # 1. Luăm datele reale
            analysis = await get_market_analysis()
            
            if "error" in analysis:
                continue
            
            signal_action = None
            verdict = analysis['signal']
            
            # 2. Verificăm dacă verdictul s-a schimbat
            if verdict == "Buy" and last_signal_type != "Buy":
                signal_action = verdict
                last_signal_type = "Buy"
            elif verdict == "Sell" and last_signal_type != "Sell":
                signal_action = verdict
                last_signal_type = "Sell"
            
            # Dacă nu e semnal, doar afișăm în consolă statusul
            if not signal_action:
                logger.info(f"Gold: {analysis['price']} | RSI={analysis['rsi']} | {verdict}")
                continue

            # 3. Construim mesajul
            message = (
                f"🏆 **XAUUSD (GOLD)**\n"
                f"Signal: **{signal_action}** 🟢🔴\n"
                f"Entry price: `{analysis['price']}`\n\n"
                f"🎯 **TP 1(SAFE):** `{analysis['tp1']}`\n"
                f"🎯 **TP 2(Risk active):** `{analysis['tp2']}`\n"
                f"🎯 **TP 3(BIG RISK):** `{analysis['tp3']}`\n\n"
                f"🛡️ **SL:** `{analysis['sl']}`"
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
