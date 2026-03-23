# main.py
import sys
import asyncio
import logging
import hmac
import hashlib
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import BufferedInputFile
from config import BOT_TOKEN, PAIRS_CONFIG, LEMONSQUEEZY_WEBHOOK_SECRET, WEBHOOK_PORT
from database import init_db, get_active_users, extend_subscription
from handlers import router
from market_data import get_market_analysis

# Configurare logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- LEMON SQUEEZY WEBHOOK HANDLER ---
async def lemonsqueezy_webhook_handle(request):
    # 1. Verificare semnătură (Securitate)
    payload = await request.read()
    signature = request.headers.get('X-Signature')
    
    if not signature or not LEMONSQUEEZY_WEBHOOK_SECRET:
        return web.Response(status=401)

    digest = hmac.new(LEMONSQUEEZY_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(digest, signature):
        logger.error("❌ Semnătură webhook invalidă!")
        return web.Response(status=401)

    # 2. Procesare date
    data = await request.json()
    event_name = data.get('meta', {}).get('event_name')

    if event_name == 'order_created':
        attributes = data['data']['attributes']
        custom_data = data['meta']['custom_data']
        
        telegram_id = custom_data.get('user_id')
        # În producție, poți calcula zilele în funcție de variant_id
        # Aici punem default 30 de zile pentru exemplu
        days = 30 
        
        if telegram_id:
            await extend_subscription(int(telegram_id), days)
            logger.info(f"✅ Plată Lemon Squeezy confirmată pentru {telegram_id}")

    return web.Response(status=200)

async def market_scanner(bot: Bot):
    """Rulează în fundal și caută semnale."""
    logger.info(f"📡 Scanner pornit pentru {len(PAIRS_CONFIG)} perechi...")
    
    # Ținem minte ultimul semnal ca să nu spamăm
    last_signal_types = {pair: None for pair in PAIRS_CONFIG}
    
    while True:
        await asyncio.sleep(10)  # Verificăm piața la fiecare 10 secunde
        
        for symbol, settings in PAIRS_CONFIG.items():
            try:
                # 1. Luăm datele reale cu factorul de risc specific
                analysis = await get_market_analysis(symbol, settings['risk'])
                
                if "error" in analysis:
                    continue
                
                signal_action = None
                verdict = analysis['signal']
                
                # Log periodic (Afișăm mereu în terminal pentru monitorizare)
                logger.info(f"{settings['name']}: {analysis['price']} | RSI={analysis['rsi']} | {verdict}")

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
    
    # 5. Pornire Server Webhook (pentru Stripe)
    app = web.Application()
    app.router.add_post('/lemonsqueezy_webhook', lemonsqueezy_webhook_handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
    await site.start()
    logger.info(f"🌍 Webhook Server ascultă pe portul {WEBHOOK_PORT}")

    # 6. Start bot polling
    logger.info("Botul a pornit! 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot oprit manual.")
