from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, UserWatchlist


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> tuple[User, bool]:
    """Obține sau creează un utilizator pe baza telegram_id."""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        # Actualizăm metadatele dacă s-au schimbat
        updated = False
        if username and user.username != username:
            user.username = username
            updated = True
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            updated = True
        if not user.is_active:
            user.is_active = True
            updated = True
        if updated:
            await session.flush()
        return user, False

    new_user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        is_active=True,
    )
    session.add(new_user)
    await session.flush()
    return new_user, True


async def get_user_watchlist(
    session: AsyncSession, telegram_id: int
) -> list[UserWatchlist]:
    """Returnează lista de simboluri urmărite pentru un utilizator."""
    stmt = (
        select(UserWatchlist)
        .join(User)
        .where(User.telegram_id == telegram_id)
        .order_by(UserWatchlist.symbol.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def add_symbol_to_watchlist(
    session: AsyncSession,
    telegram_id: int,
    symbol: str,
    alert_threshold_percent: float = 2.0,
    target_price: float | None = None,
    current_price: float | None = None,
) -> tuple[UserWatchlist | None, str]:
    """Adaugă un simbol în watchlist-ul utilizatorului."""
    user, _ = await get_or_create_user(session, telegram_id)
    symbol = symbol.upper().strip()

    # Verificăm dacă există deja
    stmt = select(UserWatchlist).where(
        UserWatchlist.user_id == user.id,
        UserWatchlist.symbol == symbol,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return existing, "already_exists"

    watchlist_item = UserWatchlist(
        user_id=user.id,
        symbol=symbol,
        alert_threshold_percent=alert_threshold_percent,
        target_price=target_price,
        last_checked_price=current_price,
    )
    session.add(watchlist_item)
    await session.flush()
    return watchlist_item, "created"


async def remove_symbol_from_watchlist(
    session: AsyncSession, telegram_id: int, symbol: str
) -> bool:
    """Șterge un simbol din watchlist-ul utilizatorului."""
    stmt = (
        select(UserWatchlist)
        .join(User)
        .where(User.telegram_id == telegram_id, UserWatchlist.symbol == symbol.upper().strip())
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        return False

    await session.delete(item)
    await session.flush()
    return True


from sqlalchemy.orm import selectinload


async def get_all_active_watchlists(session: AsyncSession) -> list[UserWatchlist]:
    """Returnează toate intrările de watchlist pentru utilizatorii activi."""
    stmt = (
        select(UserWatchlist)
        .join(User)
        .options(selectinload(UserWatchlist.user))
        .where(User.is_active.is_(True))
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_watchlist_price_and_alert(
    session: AsyncSession,
    watchlist_id: int,
    current_price: float,
    alert_triggered: bool = False,
) -> None:
    """Actualizează ultimul preț verificat și timestamp-ul alertei."""
    stmt = select(UserWatchlist).where(UserWatchlist.id == watchlist_id)
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if item:
        item.last_checked_price = current_price
        if alert_triggered:
            item.last_alert_at = datetime.now(timezone.utc)
        await session.flush()
