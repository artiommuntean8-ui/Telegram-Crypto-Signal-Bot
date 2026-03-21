# config.py
import os
from dotenv import load_dotenv

# Încarcă variabilele din fișierul .env (dacă există)
load_dotenv()

# Înlocuiește cu token-ul primit de la @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Numele fișierului de bază de date
DB_NAME = "trading_bot.db"
