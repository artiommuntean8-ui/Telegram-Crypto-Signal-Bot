# config.py
import os
from dotenv import load_dotenv

# Încarcă variabilele din fișierul .env (dacă există)
load_dotenv()

# Înlocuiește cu token-ul primit de la @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Cheia de criptare pentru datele din baza de date
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Adresa portofelului tău TON (unde primești banii)
# Asigură-te că adresa de mai jos este cea corectă
TON_WALLET_ADDRESS = os.getenv("TON_WALLET_ADDRESS", "UQA4fTmPZAVsOGlu7-5HBpBpNzHWkQ5aX4VSrCIwvOT1Y37Q")

# Link-ul tău de Telegram pentru suport (unde trimit userii dovada plății)
ADMIN_LINK = os.getenv("ADMIN_LINK", "https://t.me/username_tau")

# Configurare Produse (Prețuri în USD și echivalent TON)
# Aproximare: 1 TON ≈ 5 USD (Poți ajusta manual)
TON_PRODUCTS = {
    "weekly": {
        "name": "Abonament Săptămânal",
        "price_usd": 15,
        "price_ton": 11.62,
        "days": 7
    },
    "monthly": {
        "name": "Abonament Lunar",
        "price_usd": 45,
        "price_ton": 34.86,
        "days": 30
    },
    "yearly": {
        "name": "Abonament Anual",
        "price_usd": 400,
        "price_ton": 309.84,
        "days": 365
    }
}

# Numele fișierului de bază de date
DB_NAME = "trading_bot.db"

# Listă de ID-uri utilizatori permiși.
# Citește din .env un string de forma "123456,789012" și îl convertește în listă de int.
raw_allowed = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = [int(x.strip()) for x in raw_allowed.split(",") if x.strip()]

# Configurare Perechi Monitorizate
# risk: Procentul pentru SL (0.0015 = 0.15% pentru Gold, 0.01 = 1% pentru Crypto)
PAIRS_CONFIG = {
    # Folosim PAXG ca sursă de date, dar afișăm XAUUSD
    "PAXGUSDT": {"name": "XAUUSD", "risk": 0.0015}
}
