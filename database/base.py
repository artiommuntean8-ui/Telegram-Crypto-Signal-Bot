from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from config import settings


class Base(AsyncAttrs, DeclarativeBase):
    """Clasa de bază declarativă pentru toate modelele ORM."""
    pass


# Configurare engine asincron
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

# Factory pentru sesiuni asincrone
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Context manager asincron pentru gestionarea ciclului de viață al sesiunilor DB."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
