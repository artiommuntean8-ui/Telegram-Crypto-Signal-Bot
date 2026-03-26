# database.py
import sys
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, DateTime, Float, select, update, TypeDecorator, or_
from cryptography.fernet import Fernet
from config import DB_NAME, ENCRYPTION_KEY, ALLOWED_USERS

# Configurare Motor DB Async
engine = create_async_engine(f"sqlite+aiosqlite:///{DB_NAME}", echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# --- SECURITATE / CRIPTARE ---
if not ENCRYPTION_KEY:
    print("❌ EROARE CRITICĂ: Lipsește ENCRYPTION_KEY din .env!")
    sys.exit(1)

fernet = Fernet(ENCRYPTION_KEY)

class EncryptedString(TypeDecorator):
    """Tip de date personalizat pentru criptare automată în DB."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Criptează datele înainte de a le salva."""
        if value is not None:
            if isinstance(value, str):
                value = value.encode()
            return fernet.encrypt(value).decode('utf-8')
        return value

    def process_result_value(self, value, dialect):
        """Decriptează datele când sunt citite."""
        if value is not None:
            try:
                return fernet.decrypt(value.encode('utf-8')).decode('utf-8')
            except Exception:
                return "[Eroare Decriptare]"
        return value

# --- MODELE ---
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    # Username-ul este acum criptat în baza de date
    username: Mapped[str] = mapped_column(EncryptedString, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Data când expiră abonamentul (Null = Fără abonament)
    subscription_expiry: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class SignalLog(Base):
    __tablename__ = "signals"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    pair: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

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

async def extend_subscription(tg_id: int, days: int):
    """Prelungește abonamentul utilizatorului cu numărul de zile specificat."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()
        
        if user:
            now = datetime.now(timezone.utc)
            # Dacă are deja abonament valid, adăugăm la data existentă
            if user.subscription_expiry and user.subscription_expiry > now:
                user.subscription_expiry += timedelta(days=days)
            else:
                # Altfel, pornim de acum
                user.subscription_expiry = now + timedelta(days=days)
            
            user.is_active = True
            await session.commit()

async def deactivate_user(tg_id: int):
    async with AsyncSessionLocal() as session:
        stmt = update(User).where(User.telegram_id == tg_id).values(is_active=False)
        await session.execute(stmt)
        await session.commit()

async def get_active_users():
    """Returnează userii cu abonament valid SAU care sunt în lista de admini (whitelist)."""
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        # Selectăm userii care sunt activi ȘI (au abonament valid SAU sunt în lista allowed_users)
        stmt = select(User.telegram_id).where(
            (User.is_active == True) & 
            (
                (User.subscription_expiry > now) | 
                (User.telegram_id.in_(ALLOWED_USERS))
            )
        )
        result = await session.execute(stmt)
        return result.scalars().all()
