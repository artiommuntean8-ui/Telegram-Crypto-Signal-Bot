import asyncio
from datetime import datetime, timezone
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from config import settings
from database.base import get_db
from database.crud import get_all_active_watchlists, update_watchlist_price_and_alert
from services.crypto_api import crypto_api

logger = logging.getLogger(__name__)


class CryptoSignalService:
    """Serviciu asincron în fundal (Background Worker) pentru monitorizarea prețurilor

    și generarea automată de semnale bazate pe praguri configurate de utilizatori.
    """

    def __init__(self, bot: Bot, check_interval: int = settings.CHECK_INTERVAL_SECONDS):
        self.bot = bot
        self.check_interval = check_interval
        self._shutdown_event = asyncio.Event()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Pornește worker-ul asincron în fundal."""
        if self._task is None or self._task.done():
            self._shutdown_event.clear()
            self._task = asyncio.create_task(self._run_loop(), name="crypto_signal_monitor")
            logger.info(f"CryptoSignalService a fost pornit (interval={self.check_interval}s).")

    async def stop(self) -> None:
        """Oprește graceful worker-ul asincron."""
        if self._task and not self._task.done():
            logger.info("Oprire solicitată pentru CryptoSignalService...")
            self._shutdown_event.set()
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
            logger.info("CryptoSignalService a fost oprit.")

    async def _run_loop(self) -> None:
        """Bucla asincronă principală de verificare a pieței."""
        while not self._shutdown_event.is_set():
            try:
                await self.check_and_broadcast_signals()
            except Exception as err:
                logger.error(f"Eroare neprevăzută în bucla CryptoSignalService: {err}", exc_info=True)

            try:
                # Folosim wait_for pe shutdown_event pentru a reacționa instant la oprire
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=self.check_interval)
            except asyncio.TimeoutError:
                pass

    async def check_and_broadcast_signals(self) -> None:
        """Preia watchlists active, verifică prețurile pe Binance și trimite semnale."""
        async with get_db() as session:
            watchlists = await get_all_active_watchlists(session)

        if not watchlists:
            logger.debug("Nicio monedă în watchlist-ul utilizatorilor activi.")
            return

        # Grupăm simbolurile unice pentru a reduce cererile de rețea
        unique_symbols = {w.symbol for w in watchlists}
        logger.info(f"Monitorizare semnale pentru {len(unique_symbols)} simboluri unice din {len(watchlists)} alerte active...")

        # Preluăm datele 24hr ticker pentru fiecare simbol activ
        symbol_data = {}
        for symbol in unique_symbols:
            ticker = await crypto_api.get_24hr_ticker(symbol)
            if ticker:
                symbol_data[symbol] = ticker
            await asyncio.sleep(0.05)  # Mic delay pentru rate-limit protection

        now = datetime.now(timezone.utc)

        # Evaluăm fiecare watchlist în parte
        for item in watchlists:
            ticker = symbol_data.get(item.symbol)
            if not ticker:
                continue

            current_price = ticker.last_price
            prev_price = item.last_checked_price

            # Calculăm variația procentuală față de ultima verificare salvată
            price_delta_pct = 0.0
            if prev_price and prev_price > 0:
                price_delta_pct = ((current_price - prev_price) / prev_price) * 100.0

            should_alert = False
            signal_type = "UPDATE"
            reason = ""

            # 1. Verificare prag personalizat configurat de utilizator (alert_threshold_percent)
            if prev_price and abs(price_delta_pct) >= item.alert_threshold_percent:
                should_alert = True
                if price_delta_pct > 0:
                    signal_type = "BULLISH BREAKOUT 🟢"
                    reason = f"Prețul a crescut cu +{price_delta_pct:.2f}% (prag: {item.alert_threshold_percent}%)"
                else:
                    signal_type = "BEARISH DUMP 🔴"
                    reason = f"Prețul a scăzut cu {price_delta_pct:.2f}% (prag: {item.alert_threshold_percent}%)"

            # 2. Verificare atingere Target Price
            elif item.target_price and prev_price:
                if (prev_price < item.target_price <= current_price) or (prev_price > item.target_price >= current_price):
                    should_alert = True
                    signal_type = "🎯 TARGET ATINS"
                    reason = f"Prețul a atins ținta ta de ${item.target_price:,.4f}"

            # 3. Verificare momentum mare pe 24h dacă nu există un preț anterior
            elif prev_price is None and abs(ticker.price_change_percent) >= 5.0:
                should_alert = True
                signal_type = "24H VOLATILITATE MARE ⚡"
                reason = f"Mișcare puternică în 24h: {ticker.price_change_percent:+.2f}%"

            # Protecție anti-spam: minim 5 minute între alerte consecutive pe aceeași monedă
            if should_alert and item.last_alert_at:
                minutes_since_last = (now - item.last_alert_at).total_seconds() / 60.0
                if minutes_since_last < 5.0:
                    should_alert = False

            if should_alert:
                # Calcul niveluri standard Take Profit și Stop Loss (RRR 1:1.5)
                tp1 = current_price * (1.015 if "BULLISH" in signal_type or price_delta_pct >= 0 else 0.985)
                tp2 = current_price * (1.030 if "BULLISH" in signal_type or price_delta_pct >= 0 else 0.970)
                sl = current_price * (0.985 if "BULLISH" in signal_type or price_delta_pct >= 0 else 1.015)

                message = (
                    f"🚨 <b>SEMNAL CRYPTO: {item.symbol}</b>\n\n"
                    f"📊 <b>Verdict:</b> {signal_type}\n"
                    f"📝 <b>Motiv:</b> {reason}\n\n"
                    f"💵 <b>Preț Curent:</b> <code>${current_price:,.4f}</code>\n"
                    f"📈 <b>Variație 24h:</b> <code>{ticker.price_change_percent:+.2f}%</code>\n"
                    f"🏔 <b>High 24h:</b> <code>${ticker.high_price:,.4f}</code>\n"
                    f"📉 <b>Low 24h:</b> <code>${ticker.low_price:,.4f}</code>\n\n"
                    f"🎯 <b>Take Profit 1:</b> <code>${tp1:,.4f}</code>\n"
                    f"🎯 <b>Take Profit 2:</b> <code>${tp2:,.4f}</code>\n"
                    f"🛡 <b>Stop Loss:</b> <code>${sl:,.4f}</code>\n\n"
                    f"⏰ <i>{now.strftime('%d.%m.%Y %H:%M:%S UTC')}</i>"
                )

                try:
                    await self.bot.send_message(
                        chat_id=item.user.telegram_id,
                        text=message,
                        parse_mode="HTML",
                    )
                    logger.info(f"Semnal trimis către Telegram ID {item.user.telegram_id} pentru {item.symbol}")
                except TelegramAPIError as tg_err:
                    logger.warning(f"Nu s-a putut trimite mesajul la {item.user.telegram_id}: {tg_err}")

            # Actualizăm baza de date cu noul preț verificat
            async with get_db() as session:
                await update_watchlist_price_and_alert(
                    session=session,
                    watchlist_id=item.id,
                    current_price=current_price,
                    alert_triggered=should_alert,
                )
