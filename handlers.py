# handlers.py
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from database import add_user, deactivate_user
from market_data import get_market_analysis

# Router-ul gestionează rutele (comenzile)
router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    status = await add_user(message.from_user.id, message.from_user.username)
    
    text = f"Salut, {message.from_user.full_name}! 📈\n\n"
    text += "🤖 **Bine ai venit la Crypto Signal AI!**\n"
    text += "Acest bot monitorizează piața 24/7 și îți trimite semnale automate de trading.\n\n"

    if status == "new":
        text += "✅ **Abonament Activat:** Vei primi notificări instant când apar oportunități."
    elif status == "reactivated":
        text += "🔄 **Bine ai revenit!** Abonamentul tău a fost reactivat."
    else:
        text += "ℹ️ **Info:** Ești deja abonat și monitorizezi piața."
        
    await message.answer(text)

@router.message(Command("stop"))
async def cmd_stop(message: types.Message):
    await deactivate_user(message.from_user.id)
    await message.answer("❌ Te-ai dezabonat. Nu vei mai primi semnale.")

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    """Verifică piața la cerere."""
    msg = await message.answer("🔍 Analizez piața Binance...")
    data = await get_market_analysis()
    
    text = (f"📊 **ANALIZĂ LIVE BTC/USDT**\n\n"
            f"💰 Preț: `{data['price']}$`\n"
            f"📈 RSI: `{data['rsi']}`\n"
            f"📉 Trend SMA: `{data['sma']}$`\n\n"
            f"📢 **Verdict:** {data['signal']}")
    
    await msg.edit_text(text, parse_mode="Markdown")
