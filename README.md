# 🏆 Gold Signal AI Bot (XAUUSD)

Un bot de Telegram avansat, care monitorizează piața Aurului (XAUUSD) în timp real și trimite semnale de tranzacționare profesionale cu SL și TP multiplu.

## 🚀 Funcționalități

- **Instrument:** Monitorizează XAUUSD (via PAXGUSDT pe Binance pentru date live gratuite).
- **Analiză Tehnică:** RSI + SMA pe timeframe de 1 minut (Scalping).
- **Semnale Automate:**
  - **Buy:** RSI < 30.
  - **Sell:** RSI > 70.
  - Include **Entry Price, SL, TP1, TP2, TP3**.
- **Management Utilizatori:** Sistem de abonare/dezabonare cu bază de date SQLite.
- **Arhitectură Asincronă:** Folosește `aiogram` și `aiohttp` pentru performanță maximă (non-blocking).
- **Securitate:** Token-ul și configurările sensibile sunt încărcate din variabile de mediu (`.env`).

## 📂 Structura Proiectului

- `main.py`: Punctul de intrare. Rulează botul și scannerul de piață (background task).
- `handlers.py`: Gestionează comenzile utilizatorilor (`/start`, `/stop`).
- `database.py`: Definește modelele bazei de date și funcțiile de interacțiune (SQLAlchemy).
- `config.py`: Fișierul de configurare pentru Token și alte constante.
- `requirements.txt`: Lista dependențelor necesare.

## 🛠️ Instalare și Rulare

### 1. Cerințe preliminare
Ai nevoie de Python 3.8+ instalat.

### 2. Clonarea și Instalarea Dependențelor
Deschide terminalul în folderul proiectului și rulează:

```bash
pip install -r requirements.txt
```

### 3. Configurare
Editează fișierul `config.py` și adaugă token-ul primit de la @BotFather:

```python
BOT_TOKEN = "TOKENUL_TAU_AICI"
```

### 4. Pornire
Rulează botul:

```bash
python main.py
```

Botul va crea automat fișierul `trading_bot.db` la prima rulare.

## 🎮 Comenzi Telegram

- `/start` - Te abonezi la fluxul de semnale.
- `/stop` - Te dezabonezi de la semnale.

## ⚠️ Disclaimer

Acest software este un **MVP (Minimum Viable Product)** educațional. Strategia RSI implementată este una de bază.

**Nu este un sfat financiar.** Tranzacționarea criptomonedelor implică riscuri majore. Autorul nu este responsabil pentru eventualele pierderi financiare rezultate din utilizarea acestui bot.

---
Dezvoltat cu ❤️ folosind Python & Aiogram.