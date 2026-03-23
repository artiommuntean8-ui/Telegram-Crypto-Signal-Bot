# config.py
import os
from dotenv import load_dotenv

# Încarcă variabilele din fișierul .env (dacă există)
load_dotenv()

# Înlocuiește cu token-ul primit de la @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Numele fișierului de bază de date
DB_NAME = "trading_bot.db"

# Listă de ID-uri utilizatori permiși.
# Citește din .env un string de forma "123456,789012" și îl convertește în listă de int.
raw_allowed = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = [int(x.strip()) for x in raw_allowed.split(",") if x.strip()]
