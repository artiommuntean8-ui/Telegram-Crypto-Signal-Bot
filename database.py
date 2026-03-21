# database.py
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, DateTime, Float, select, update
from config import DB_NAME

# Configurare Motor DB Async
engine = create_async_engine(f"sqlite+aiosqlite:///{DB_NAME}", echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# --- MODELE ---
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SignalLog(Base):
    __tablename__ = "signals"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    pair: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# --- FUNCȚII AJUTĂTOARE ---
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def add_user(tg_id: int, username: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()
        
        if not user:
            new_user = User(telegram_id=tg_id, username=username, is_active=True)
            session.add(new_user)
            await session.commit()
            return "new"
        elif not user.is_active:
            user.is_active = True
            await session.commit()
            return "reactivated"
        return "exists"

async def deactivate_user(tg_id: int):
    async with AsyncSessionLocal() as session:
        stmt = update(User).where(User.telegram_id == tg_id).values(is_active=False)
        await session.execute(stmt)
        await session.commit()

async def get_active_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.telegram_id).where(User.is_active == True))
        return result.scalars().all()
