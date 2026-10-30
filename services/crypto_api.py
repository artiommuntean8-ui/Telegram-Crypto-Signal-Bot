import asyncio
import logging
from typing import Any
import aiohttp
from pydantic import BaseModel, ConfigDict, Field

from config import settings

logger = logging.getLogger(__name__)


class TickerPrice(BaseModel):
    """Schema Pydantic pentru validarea răspunsului de preț instant."""

    symbol: str
    price: float

    model_config = ConfigDict(populate_by_name=True)


class Ticker24hr(BaseModel):
    """Schema Pydantic pentru datele de analiză pe 24 de ore."""

    symbol: str
    price_change: float = Field(alias="priceChange")
    price_change_percent: float = Field(alias="priceChangePercent")
    last_price: float = Field(alias="lastPrice")
    high_price: float = Field(alias="highPrice")
    low_price: float = Field(alias="lowPrice")
    volume: float = Field(alias="volume")
    quote_volume: float = Field(alias="quoteVolume")

    model_config = ConfigDict(populate_by_name=True)


def normalize_symbol(symbol: str) -> str:
    """Normalizează simbolul (ex: 'btc', 'btc/usdt', 'btc-usdt' -> 'BTCUSDT')."""
    clean = symbol.upper().replace("/", "").replace("-", "").replace("_", "").strip()
    
    # Citate comune pe Binance
    common_quotes = ("USDT", "FDUSD", "USDC", "EUR", "TRY")
    has_quote = any(clean.endswith(q) for q in common_quotes) or (
        len(clean) >= 6 and (clean.endswith("BTC") or clean.endswith("ETH"))
    )
    if not has_quote:
        clean = f"{clean}USDT"
    return clean


class BinancePublicAPI:
    """Client asincron de producție pentru Binance Public API (folosind aiohttp)."""

    def __init__(self, base_url: str = settings.BINANCE_BASE_URL, timeout: float = settings.REQUEST_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Asigură un ClientSession de tip pool reutilizabil (Singleton pattern per instanță)."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def close(self) -> None:
        """Închide sesiunea aiohttp la oprirea aplicației."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("Sesiunea aiohttp către Binance API a fost închisă.")

    async def get_current_price(self, symbol: str) -> TickerPrice | None:
        """Preia prețul curent pentru un simbol validat cu Pydantic."""
        normalized = normalize_symbol(symbol)
        url = f"{self.base_url}/api/v3/ticker/price"
        params = {"symbol": normalized}

        session = await self.get_session()
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data: dict[str, Any] = await response.json()
                    return TickerPrice.model_validate(data)
                elif response.status == 400:
                    logger.warning(f"Simbol invalid solicitat la Binance: {normalized}")
                    return None
                else:
                    logger.error(f"Eroare API Binance ({response.status}) la get_current_price pentru {normalized}")
                    return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            logger.error(f"Eroare rețea la preluarea prețului pentru {normalized}: {err}")
            return None
        except Exception as err:
            logger.error(f"Eroare neașteptată la validarea prețului pentru {normalized}: {err}")
            return None

    async def get_24hr_ticker(self, symbol: str) -> Ticker24hr | None:
        """Preia statisticile pe 24h pentru un simbol (schimbare %, volum, high/low)."""
        normalized = normalize_symbol(symbol)
        url = f"{self.base_url}/api/v3/ticker/24hr"
        params = {"symbol": normalized}

        session = await self.get_session()
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data: dict[str, Any] = await response.json()
                    return Ticker24hr.model_validate(data)
                elif response.status == 400:
                    logger.warning(f"Simbol invalid solicitat la 24hr ticker: {normalized}")
                    return None
                else:
                    logger.error(f"Eroare API Binance ({response.status}) la get_24hr_ticker pentru {normalized}")
                    return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            logger.error(f"Eroare rețea la preluarea 24hr ticker pentru {normalized}: {err}")
            return None
        except Exception as err:
            logger.error(f"Eroare neașteptată la validarea 24hr ticker pentru {normalized}: {err}")
            return None

    async def validate_symbol(self, symbol: str) -> bool:
        """Verifică dacă un simbol este valid și tranzacționabil pe Binance."""
        result = await self.get_current_price(symbol)
        return result is not None

    async def get_all_prices(self) -> dict[str, float]:
        """Preia dintr-un singur apel HTTP toate prețurile curente (util pentru background monitor)."""
        url = f"{self.base_url}/api/v3/ticker/price"
        session = await self.get_session()
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Mapăm {'BTCUSDT': 67450.0, ...}
                    return {item["symbol"]: float(item["price"]) for item in data}
                else:
                    logger.error(f"Eroare API Binance ({response.status}) la get_all_prices")
                    return {}
        except Exception as err:
            logger.error(f"Eroare la get_all_prices: {err}")
            return {}


# Instanță singleton a clientului API
crypto_api = BinancePublicAPI()
