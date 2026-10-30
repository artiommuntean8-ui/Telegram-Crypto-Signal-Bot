from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.models import UserWatchlist


def get_main_menu_kb() -> InlineKeyboardMarkup:
    """Meniul principal al botului."""
    keyboard = [
        [
            InlineKeyboardButton(text="📋 Watchlist-ul Meu", callback_data="menu:watchlist"),
            InlineKeyboardButton(text="🔍 Preț Instant", callback_data="menu:check_price"),
        ],
        [
            InlineKeyboardButton(text="➕ Adaugă Monedă", callback_data="menu:add_symbol"),
            InlineKeyboardButton(text="➖ Șterge Monedă", callback_data="menu:delete_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_watchlist_kb(items: list[UserWatchlist]) -> InlineKeyboardMarkup:
    """Tastatură pentru afișarea listei de monede urmărite."""
    keyboard: list[list[InlineKeyboardButton]] = []

    # Butoane per monedă (câte 2 pe rând pentru o așezare compactă)
    row: list[InlineKeyboardButton] = []
    for item in items:
        row.append(InlineKeyboardButton(text=f"🪙 {item.symbol}", callback_data=f"crypto:view:{item.symbol}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Butoane de acțiune
    keyboard.append([
        InlineKeyboardButton(text="➕ Adaugă", callback_data="menu:add_symbol"),
        InlineKeyboardButton(text="➖ Șterge", callback_data="menu:delete_menu"),
    ])
    keyboard.append([
        InlineKeyboardButton(text="🔄 Reîmprospătează", callback_data="menu:watchlist"),
        InlineKeyboardButton(text="🔙 Meniu Principal", callback_data="menu:main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_delete_symbols_kb(items: list[UserWatchlist]) -> InlineKeyboardMarkup:
    """Tastatură pentru selectarea monedei de șters."""
    keyboard: list[list[InlineKeyboardButton]] = []

    for item in items:
        keyboard.append([
            InlineKeyboardButton(
                text=f"❌ Șterge {item.symbol}",
                callback_data=f"crypto:delete:{item.symbol}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔙 Înapoi la Watchlist", callback_data="menu:watchlist")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_symbol_detail_kb(symbol: str, in_watchlist: bool = True) -> InlineKeyboardMarkup:
    """Tastatură pentru ecranul de detalii al unui simbol."""
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Actualizează Preț", callback_data=f"crypto:view:{symbol}"),
        ]
    ]

    if in_watchlist:
        keyboard.append([
            InlineKeyboardButton(text="❌ Șterge din Watchlist", callback_data=f"crypto:delete:{symbol}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(text="➕ Adaugă în Watchlist", callback_data=f"crypto:quick_add:{symbol}")
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔙 Înapoi la Watchlist", callback_data="menu:watchlist")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cancel_kb() -> InlineKeyboardMarkup:
    """Buton de anulare a stării FSM curente."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Anulează", callback_data="menu:main")]]
    )
