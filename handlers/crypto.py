import asyncio
import logging
from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.base import get_db
from database.crud import (
    add_symbol_to_watchlist,
    get_or_create_user,
    get_user_watchlist,
    remove_symbol_from_watchlist,
)
from keyboards.crypto_kb import (
    get_cancel_kb,
    get_delete_symbols_kb,
    get_main_menu_kb,
    get_symbol_detail_kb,
    get_watchlist_kb,
)
from services.crypto_api import crypto_api, normalize_symbol

logger = logging.getLogger(__name__)

router = Router(name="crypto_router")


class CryptoStates(StatesGroup):
    """Stări FSM pentru fluxurile interactive de adăugare și căutare."""

    waiting_for_symbol_to_add = State()
    waiting_for_symbol_to_check = State()


# ---------------------------------------------------------
# MENIU PRINCIPAL & START
# ---------------------------------------------------------

@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start_or_menu(message: types.Message, state: FSMContext):
    """Înregistrează utilizatorul și afișează panoul principal de control."""
    await state.clear()

    async with get_db() as session:
        user, is_new = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

    greeting = "Bine ai revenit" if not is_new else "Bun venit"
    text = (
        f"👋 <b>{greeting}, {message.from_user.first_name}!</b>\n\n"
        "🤖 <b>Crypto Signal Pro Bot</b>\n"
        "Monitorizează piața crypto în timp real direct prin Binance Public API.\n\n"
        "⚡ <b>Funcționalități cheie:</b>\n"
        "• 📋 <b>Watchlist Personalizat:</b> Urmărește monedele tale favorite.\n"
        "• 🔍 <b>Preț Instant:</b> Verifică orice pereche crypto în secunde.\n"
        "• 🚨 <b>Semnale Automate:</b> Alerte în fundal la variații de preț și ținte atinse.\n\n"
        "Alege o opțiune din meniul de mai jos:"
    )

    await message.answer(text, reply_markup=get_main_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Revine la meniul principal."""
    await state.clear()
    await callback.answer()

    text = (
        f"🏠 <b>Meniu Principal</b>\n\n"
        f"Selectează o acțiune pentru a gestiona monedele urmărite sau a verifica piața:"
    )

    try:
        await callback.message.edit_text(text, reply_markup=get_main_menu_kb(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_main_menu_kb(), parse_mode="HTML")


# ---------------------------------------------------------
# VIZUALIZARE WATCHLIST
# ---------------------------------------------------------

@router.callback_query(F.data == "menu:watchlist")
async def cb_view_watchlist(callback: types.CallbackQuery, state: FSMContext):
    """Afișează watchlist-ul utilizatorului cu prețuri actualizate în timp real."""
    await state.clear()
    await callback.answer("Se încarcă datele...")

    async with get_db() as session:
        items = await get_user_watchlist(session, callback.from_user.id)

    if not items:
        text = (
            "📋 <b>Watchlist-ul Tău este gol!</b>\n\n"
            "Nu ai adăugat încă nicio monedă în lista de urmărire.\n"
            "Apasă butonul de mai jos pentru a începe să primești semnale."
        )
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="➕ Adaugă Prima Monedă", callback_data="menu:add_symbol")],
                [types.InlineKeyboardButton(text="🔙 Meniu Principal", callback_data="menu:main")],
            ]
        )
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        return

    # Preluăm datele live în paralel pentru toate monedele din watchlist
    tasks = [crypto_api.get_24hr_ticker(item.symbol) for item in items]
    tickers = await asyncio.gather(*tasks, return_exceptions=True)

    lines = ["📋 <b>Watchlist-ul Tău (Live Binance):</b>\n"]
    for item, ticker in zip(items, tickers):
        if isinstance(ticker, Exception) or ticker is None:
            lines.append(f"• <b>{item.symbol}</b>: <i>indisponibil momentan</i>")
        else:
            delta_icon = "🟢" if ticker.price_change_percent >= 0 else "🔴"
            lines.append(
                f"• <b>{ticker.symbol}</b>: <code>${ticker.last_price:,.4f}</code> "
                f"({delta_icon} {ticker.price_change_percent:+.2f}%)"
            )

    lines.append("\n<i>Apasă pe un simbol de mai jos pentru opțiuni detaliate:</i>")
    text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=get_watchlist_kb(items),
        parse_mode="HTML",
    )


# ---------------------------------------------------------
# ADĂUGARE MONEDĂ ÎN WATCHLIST
# ---------------------------------------------------------

@router.callback_query(F.data == "menu:add_symbol")
async def cb_start_add_symbol(callback: types.CallbackQuery, state: FSMContext):
    """Inițiază starea de adăugare a unei monede."""
    await callback.answer()
    await state.set_state(CryptoStates.waiting_for_symbol_to_add)

    text = (
        "➕ <b>Adăugare Monedă în Watchlist</b>\n\n"
        "Trimite simbolul monedei pe care dorești să o urmărești.\n"
        "Exemple: <code>BTC</code>, <code>ETH</code>, <code>SOL</code>, <code>BTCUSDT</code>\n\n"
        "<i>Botul va verifica automat dacă perechea există pe Binance.</i>"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_kb(), parse_mode="HTML")


@router.message(CryptoStates.waiting_for_symbol_to_add)
async def process_add_symbol(message: types.Message, state: FSMContext):
    """Procesează simbolul trimis de utilizator și îl salvează în DB."""
    raw_symbol = message.text.strip()
    normalized = normalize_symbol(raw_symbol)

    # Verificare live pe Binance
    ticker = await crypto_api.get_24hr_ticker(normalized)
    if not ticker:
        await message.answer(
            f"❌ Simbolul <b>{raw_symbol}</b> (normalizat ca <code>{normalized}</code>) "
            f"nu a fost găsit pe Binance sau nu este activ.\n\n"
            "Te rugăm să reîncerci (ex: <b>BTC</b>, <b>SOL</b>, <b>ETHUSDT</b>):",
            reply_markup=get_cancel_kb(),
            parse_mode="HTML",
        )
        return

    # Salvare în baza de date
    async with get_db() as session:
        _, status = await add_symbol_to_watchlist(
            session=session,
            telegram_id=message.from_user.id,
            symbol=normalized,
            current_price=ticker.last_price,
        )

    await state.clear()

    if status == "already_exists":
        await message.answer(
            f"ℹ️ Simbolul <b>{normalized}</b> se află deja în watchlist-ul tău!",
            reply_markup=get_main_menu_kb(),
            parse_mode="HTML",
        )
    else:
        text = (
            f"✅ <b>{normalized} a fost adăugat cu succes în Watchlist!</b>\n\n"
            f"💵 <b>Preț Curent:</b> <code>${ticker.last_price:,.4f}</code>\n"
            f"📈 <b>Variație 24h:</b> <code>{ticker.price_change_percent:+.2f}%</code>\n\n"
            f"🔔 Botul va monitoriza această monedă și îți va trimite alerte automate în fundal."
        )
        await message.answer(text, reply_markup=get_main_menu_kb(), parse_mode="HTML")


# ---------------------------------------------------------
# ȘTERGERE MONEDĂ DIN WATCHLIST
# ---------------------------------------------------------

@router.callback_query(F.data == "menu:delete_menu")
async def cb_delete_menu(callback: types.CallbackQuery, state: FSMContext):
    """Afișează meniul de ștergere cu butoane pentru fiecare monedă."""
    await state.clear()
    await callback.answer()

    async with get_db() as session:
        items = await get_user_watchlist(session, callback.from_user.id)

    if not items:
        await callback.answer("Nu ai nicio monedă în watchlist de șters.", show_alert=True)
        return

    text = "➖ <b>Ștergere din Watchlist</b>\n\nApasă pe moneda pe care dorești să o elimini:"
    await callback.message.edit_text(text, reply_markup=get_delete_symbols_kb(items), parse_mode="HTML")


@router.callback_query(F.data.startswith("crypto:delete:"))
async def cb_delete_symbol(callback: types.CallbackQuery, state: FSMContext):
    """Execută ștergerea monedei selectate."""
    symbol = callback.data.split(":")[2]

    async with get_db() as session:
        removed = await remove_symbol_from_watchlist(
            session=session,
            telegram_id=callback.from_user.id,
            symbol=symbol,
        )

    if removed:
        await callback.answer(f"✅ {symbol} a fost eliminat din Watchlist!", show_alert=True)
    else:
        await callback.answer(f"Moneda {symbol} nu a fost găsită.", show_alert=True)

    # Reîncărcăm watchlist-ul actualizat
    await cb_view_watchlist(callback, state)


# ---------------------------------------------------------
# VERIFICARE PREȚ INSTANT
# ---------------------------------------------------------

@router.callback_query(F.data == "menu:check_price")
async def cb_start_check_price(callback: types.CallbackQuery, state: FSMContext):
    """Inițiază căutarea unui preț instant."""
    await callback.answer()
    await state.set_state(CryptoStates.waiting_for_symbol_to_check)

    text = (
        "🔍 <b>Verificare Preț Instant</b>\n\n"
        "Introdu simbolul monedei pentru care dorești cotația în timp real.\n"
        "Exemplu: <code>BTC</code>, <code>ETH</code>, <code>SOL</code>, <code>XRP</code>, <code>DOGE</code>:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_kb(), parse_mode="HTML")


@router.message(CryptoStates.waiting_for_symbol_to_check)
async def process_check_price(message: types.Message, state: FSMContext):
    """Preia datele complete pe 24h și afișează cartonașul de preț."""
    raw_symbol = message.text.strip()
    normalized = normalize_symbol(raw_symbol)

    ticker = await crypto_api.get_24hr_ticker(normalized)
    if not ticker:
        await message.answer(
            f"❌ Simbolul <b>{raw_symbol}</b> nu a fost găsit pe Binance.\n"
            "Încearcă din nou (ex: <b>BTC</b>, <b>ETH</b>, <b>SOL</b>):",
            reply_markup=get_cancel_kb(),
            parse_mode="HTML",
        )
        return

    await state.clear()

    # Verificăm dacă este deja în watchlist-ul userului
    async with get_db() as session:
        watchlist = await get_user_watchlist(session, message.from_user.id)
    in_watchlist = any(item.symbol == normalized for item in watchlist)

    delta_emoji = "🟢" if ticker.price_change_percent >= 0 else "🔴"
    text = (
        f"📊 <b>Cotație Live: {ticker.symbol}</b>\n\n"
        f"💵 <b>Preț Curent:</b> <code>${ticker.last_price:,.4f}</code>\n"
        f"📈 <b>Variație 24h:</b> {delta_emoji} <code>{ticker.price_change_percent:+.2f}%</code>\n"
        f"🏔 <b>Maxim 24h:</b> <code>${ticker.high_price:,.4f}</code>\n"
        f"📉 <b>Minim 24h:</b> <code>${ticker.low_price:,.4f}</code>\n"
        f"📦 <b>Volum (Coin):</b> <code>{ticker.volume:,.2f}</code>\n"
        f"💰 <b>Volum (USD):</b> <code>${ticker.quote_volume:,.2f}</code>"
    )

    await message.answer(
        text,
        reply_markup=get_symbol_detail_kb(ticker.symbol, in_watchlist=in_watchlist),
        parse_mode="HTML",
    )


# ---------------------------------------------------------
# VIZUALIZARE & QUICK ADD DIN CARTONAȘ
# ---------------------------------------------------------

@router.callback_query(F.data.startswith("crypto:view:"))
async def cb_view_symbol_details(callback: types.CallbackQuery):
    """Actualizează detaliile unui simbol selectat."""
    symbol = callback.data.split(":")[2]
    await callback.answer("Actualizare preț...")

    ticker = await crypto_api.get_24hr_ticker(symbol)
    if not ticker:
        await callback.answer("Nu s-au putut prelua datele.", show_alert=True)
        return

    async with get_db() as session:
        watchlist = await get_user_watchlist(session, callback.from_user.id)
    in_watchlist = any(item.symbol == symbol for item in watchlist)

    delta_emoji = "🟢" if ticker.price_change_percent >= 0 else "🔴"
    text = (
        f"📊 <b>Cotație Live: {ticker.symbol}</b>\n\n"
        f"💵 <b>Preț Curent:</b> <code>${ticker.last_price:,.4f}</code>\n"
        f"📈 <b>Variație 24h:</b> {delta_emoji} <code>{ticker.price_change_percent:+.2f}%</code>\n"
        f"🏔 <b>Maxim 24h:</b> <code>${ticker.high_price:,.4f}</code>\n"
        f"📉 <b>Minim 24h:</b> <code>${ticker.low_price:,.4f}</code>\n"
        f"📦 <b>Volum:</b> <code>{ticker.volume:,.2f}</code>"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_symbol_detail_kb(symbol, in_watchlist=in_watchlist),
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("crypto:quick_add:"))
async def cb_quick_add(callback: types.CallbackQuery):
    """Adaugă direct simbolul în watchlist dintr-un cartonaș de preț."""
    symbol = callback.data.split(":")[2]

    price_data = await crypto_api.get_current_price(symbol)
    current_price = price_data.price if price_data else None

    async with get_db() as session:
        _, status = await add_symbol_to_watchlist(
            session=session,
            telegram_id=callback.from_user.id,
            symbol=symbol,
            current_price=current_price,
        )

    if status == "created":
        await callback.answer(f"✅ {symbol} a fost adăugat în Watchlist!", show_alert=True)
    else:
        await callback.answer(f"{symbol} este deja în Watchlist.", show_alert=True)

    await cb_view_symbol_details(callback)
