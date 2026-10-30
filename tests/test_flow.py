import asyncio
import logging
import os
import sys

# Asigură includerea directorului rădăcină în sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from database.base import get_db, Base, engine
from database.crud import (
    get_or_create_user,
    get_user_watchlist,
    add_symbol_to_watchlist,
    remove_symbol_from_watchlist,
    get_all_active_watchlists,
    update_watchlist_price_and_alert,
)
from services.crypto_api import crypto_api, normalize_symbol

logging.basicConfig(level=logging.INFO)

async def test_suite():
    print("--- 1. TEST INITIALIZARE BAZĂ DE DATE ---")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Tabele create / verificate cu succes.")

    print("\n--- 2. TEST CRUD UTILIZATOR ---")
    async with get_db() as session:
        user, is_new = await get_or_create_user(
            session=session,
            telegram_id=999888777,
            username="crypto_trader",
            first_name="Alex",
        )
        print(f"✓ Utilizator: {user.username} (ID Telegram: {user.telegram_id}, Nou: {is_new})")

    print("\n--- 3. TEST ADĂUGARE WATCHLIST ---")
    async with get_db() as session:
        # Preluăm un preț real
        ticker_btc = await crypto_api.get_current_price("BTC")
        print(f"✓ Binance API Live BTC: {ticker_btc.symbol} = ${ticker_btc.price:,.2f}")

        item_btc, status_btc = await add_symbol_to_watchlist(
            session=session,
            telegram_id=999888777,
            symbol="BTCUSDT",
            current_price=ticker_btc.price,
        )
        print(f"✓ Adăugat BTCUSDT: {status_btc} (ID: {item_btc.id})")

        ticker_eth = await crypto_api.get_current_price("ETH")
        item_eth, status_eth = await add_symbol_to_watchlist(
            session=session,
            telegram_id=999888777,
            symbol="ETHUSDT",
            current_price=ticker_eth.price,
        )
        print(f"✓ Adăugat ETHUSDT: {status_eth} (ID: {item_eth.id})")

    print("\n--- 4. TEST CITIRE WATCHLIST ---")
    async with get_db() as session:
        items = await get_user_watchlist(session, 999888777)
        print(f"✓ Monede în watchlist: {[i.symbol for i in items]}")
        assert len(items) == 2, f"Așteptam 2 monede, am găsit {len(items)}"

    print("\n--- 5. TEST GET ALL ACTIVE WATCHLISTS CU EAGER LOAD ---")
    async with get_db() as session:
        all_watchlists = await get_all_active_watchlists(session)
        print(f"✓ Total intrări active: {len(all_watchlists)}")
        for w in all_watchlists:
            print(f"  • Simbol: {w.symbol} -> User Telegram ID: {w.user.telegram_id}")

    print("\n--- 6. TEST ȘTERGERE DIN WATCHLIST ---")
    async with get_db() as session:
        removed = await remove_symbol_from_watchlist(session, 999888777, "ETHUSDT")
        print(f"✓ Ștergere ETHUSDT: {removed}")
        items_after = await get_user_watchlist(session, 999888777)
        print(f"✓ Monede rămase: {[i.symbol for i in items_after]}")
        assert len(items_after) == 1

    print("\n--- 7. TEST BINANCE 24HR TICKER MODEL PYDANTIC ---")
    ticker_24h = await crypto_api.get_24hr_ticker("SOL")
    print(f"✓ SOL 24h Ticker: Preț={ticker_24h.last_price}, Variație={ticker_24h.price_change_percent}%, High={ticker_24h.high_price}, Low={ticker_24h.low_price}")

    await crypto_api.close()
    await engine.dispose()
    print("\n🎉 TOATE TESTELE AU TRECUT CU SUCCES!")

if __name__ == "__main__":
    asyncio.run(test_suite())
