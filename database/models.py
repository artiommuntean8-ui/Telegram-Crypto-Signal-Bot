from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base


class User(Base):
    """Model pentru utilizatorii botului de Telegram."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relație 1:N cu UserWatchlist
    watchlist: Mapped[list["UserWatchlist"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="UserWatchlist.symbol",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}')>"


class UserWatchlist(Base):
    """Model pentru monedele urmărite de fiecare utilizator (Watchlist)."""

    __tablename__ = "user_watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    alert_threshold_percent: Mapped[float] = mapped_column(
        Float, default=2.0, nullable=False
    )
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_checked_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_alert_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relație N:1 către User (lazy selectin pentru siguranță în context async)
    user: Mapped["User"] = relationship(back_populates="watchlist", lazy="selectin")

    # Un user nu poate adăuga același simbol de mai multe ori
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_user_symbol"),
    )

    def __repr__(self) -> str:
        return f"<UserWatchlist(id={self.id}, user_id={self.user_id}, symbol='{self.symbol}')>"
