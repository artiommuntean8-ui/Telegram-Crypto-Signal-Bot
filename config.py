# config.py
import os
from dotenv import load_dotenv

# Încarcă variabilele din fișierul .env (dacă există)
load_dotenv()

# Înlocuiește cu token-ul primit de la @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Cheia de criptare pentru datele din baza de date
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Configurare Lemon Squeezy
LEMONSQUEEZY_API_KEY = os.getenv("LEMONSQUEEZY_API_KEY")
LEMONSQUEEZY_STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID")
LEMONSQUEEZY_WEBHOOK_SECRET = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", 8080)) # Portul pe care ascultă serverul

# Moneda pentru plăți (USD, EUR, RON). 
CURRENCY = "USD"

# Numele fișierului de bază de date
DB_NAME = "trading_bot.db"

# Listă de ID-uri utilizatori permiși.
# Citește din .env un string de forma "123456,789012" și îl convertește în listă de int.
raw_allowed = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = [int(x.strip()) for x in raw_allowed.split(",") if x.strip()]

# Configurare Perechi Monitorizate
# risk: Procentul pentru SL (0.0015 = 0.15% pentru Gold, 0.01 = 1% pentru Crypto)
PAIRS_CONFIG = {
    "PAXGUSDT": {"name": "Gold (XAUUSD)", "risk": 0.0015}
}
