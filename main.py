import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database.base import Base, engine
from handlers.crypto import router as crypto_router
from services.crypto_api import crypto_api
from services.signal_service import CryptoSignalService

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Configurare logging avansat
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("crypto_signal_bot")


async def init_database() -> None:
    """Verifică și inițializează tabelele bazei de date la pornire."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Baza de date asincronă a fost inițializată cu succes.")
    except Exception as err:
        logger.error(f"Eroare critică la inițializarea bazei de date: {err}", exc_info=True)
        sys.exit(1)


async def main() -> None:
    """Punctul principal de intrare al aplicației."""
    logger.info("Pornire Crypto Signal Bot...")

    # 1. Inițializare baza de date
    await init_database()

    # 2. Inițializare instanță Bot și Dispatcher cu DefaultBotProperties
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # 3. Înregistrare routere
    dp.include_router(crypto_router)

    # 4. Inițializare serviciu asincron de semnale
    signal_service = CryptoSignalService(
        bot=bot,
        check_interval=settings.CHECK_INTERVAL_SECONDS,
    )

    # Hook-uri de startup și shutdown
    async def startup_handler() -> None:
        logger.info("Inițializare hook-uri de startup...")
        signal_service.start()
        bot_info = await bot.get_me()
        logger.info(f"Bot autentificat ca @{bot_info.username} (ID: {bot_info.id})")

    async def shutdown_handler() -> None:
        logger.info("Eliberare resurse la oprire...")
        await signal_service.stop()
        await crypto_api.close()
        await engine.dispose()
        await bot.session.close()
        logger.info("Shutdown finalizat curat.")

    dp.startup.register(startup_handler)
    dp.shutdown.register(shutdown_handler)

    # 5. Rulare bot în regim de polling
    try:
        # Ștergem eventualele webhook-uri vechi și procesăm actualizările restante
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Polling-ul a fost pornit. Botul ascultă comenzi...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Oprire manuală detectată.")
    finally:
        await shutdown_handler()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Aplicația a fost oprită.")
