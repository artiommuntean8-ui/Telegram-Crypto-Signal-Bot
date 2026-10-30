from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Configurația aplicației utilizând variabile de mediu și Pydantic Settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    BOT_TOKEN: str = Field(..., description="Token-ul Telegram primit de la @BotFather")
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///crypto_bot.db",
        description="URL de conexiune asincronă SQLAlchemy"
    )
    BINANCE_BASE_URL: str = Field(
        default="https://api.binance.com",
        description="Endpoint de bază pentru Binance Public API"
    )
    CHECK_INTERVAL_SECONDS: int = Field(
        default=30,
        description="Intervalul în secunde pentru verificarea periodică a semnalelor"
    )
    DEFAULT_ALERT_THRESHOLD: float = Field(
        default=2.0,
        description="Pragul procentual implicit de alertă la variația prețului"
    )
    REQUEST_TIMEOUT: float = Field(
        default=10.0,
        description="Timeout în secunde pentru apelurile HTTP către API-uri externe"
    )


settings = Settings()
