# config.py
import os
from dotenv import load_dotenv

# Încarcă variabilele din fișierul .env (dacă există)
load_dotenv()

# Înlocuiește cu token-ul primit de la @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Cheia de criptare pentru datele din baza de date
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Token pentru plăți (Stripe/Provider). Ia-l de la @BotFather.
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")

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
