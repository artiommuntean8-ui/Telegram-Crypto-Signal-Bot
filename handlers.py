# handlers.py
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import BufferedInputFile, LabeledPrice, PreCheckoutQuery, ContentType
from database import add_user, deactivate_user, extend_subscription, get_active_users
from market_data import get_market_analysis
from config import ALLOWED_USERS, PAIRS_CONFIG, PAYMENT_PROVIDER_TOKEN

# Router-ul gestionează rutele (comenzile)
router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
        await message.answer("⛔ **Acces Interzis:** Nu ești pe lista de utilizatori autorizați.")
        return

    status = await add_user(message.from_user.id, message.from_user.username)
    
    text = f"Salut, {message.from_user.full_name}! 📈\n\n"
    text += "🤖 **Bine ai venit la Gold Signal AI!**\n"
    text += "Acest bot monitorizează piața XAUUSD (Aur) și trimite semnale profesionale.\n\n"

    text += "💎 **Abonamente Disponibile:**\n"
    text += "Folosește comanda /plans pentru a vedea prețurile și a te abona.\n"
    
    await message.answer(text)

@router.message(Command("plans"))
async def cmd_plans(message: types.Message):
    """Afișează opțiunile de abonament."""
    if not PAYMENT_PROVIDER_TOKEN:
        await message.answer("⚠️ Sistemul de plăți este momentan dezactivat (Missing Token).")
        return

    await message.answer("👇 **Alege planul potrivit pentru tine:**")

    # Plan Săptămânal
    await message.answer_invoice(
        title="Abonament Săptămânal",
        description="Acces 7 zile la semnale XAUUSD Premium.",
        payload="sub_weekly",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="USD", # Poți schimba în "EUR" sau "RON" dacă providerul cere
        prices=[LabeledPrice(label="7 Zile", amount=1500)], # 15.00$ (în cenți)
        start_parameter="sub-weekly"
    )

    # Plan Lunar
    await message.answer_invoice(
        title="Abonament Lunar",
        description="Acces 30 zile la semnale XAUUSD Premium. (Best Value)",
        payload="sub_monthly",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="USD",
        prices=[LabeledPrice(label="30 Zile", amount=4500)], # 45.00$
        start_parameter="sub-monthly"
    )

    # Plan Anual
    await message.answer_invoice(
        title="Abonament Anual",
        description="Acces 365 zile la semnale XAUUSD Premium.",
        payload="sub_yearly",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="USD",
        prices=[LabeledPrice(label="365 Zile", amount=40000)], # 400.00$
        start_parameter="sub-yearly"
    )

# --- PLĂȚI ---

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Telegram verifică dacă totul e ok înainte să ia banii."""
    await pre_checkout_query.answer(ok=True)

@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: types.Message):
    """Banii au fost încasați. Activăm abonamentul."""
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    
    days_to_add = 0
    plan_name = ""

    if payload == "sub_weekly":
        days_to_add = 7
        plan_name = "Săptămânal"
    elif payload == "sub_monthly":
        days_to_add = 30
        plan_name = "Lunar"
    elif payload == "sub_yearly":
        days_to_add = 365
        plan_name = "Anual"

    # Activăm în baza de date
    await extend_subscription(message.from_user.id, days_to_add)

    await message.answer(
        f"✅ **Plată Confirmată!**\n\n"
        f"Ai activat planul **{plan_name}**.\n"
        f"Vei primi semnale automat timp de {days_to_add} zile. Spor la pips! 🚀"
    )

@router.message(Command("stop"))
async def cmd_stop(message: types.Message):
    await deactivate_user(message.from_user.id)
    await message.answer("❌ Te-ai dezabonat. Nu vei mai primi semnale.")

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    """Verifică piața la cerere."""
    # Verificăm manual dacă are acces pentru comanda asta
    active_users_ids = await get_active_users()
    if message.from_user.id not in active_users_ids:
        await message.answer("⛔ **Abonament Expirat sau Inexistent.**\nFolosește /plans pentru a te abona.")
        return

    await message.answer("🔍 Analizez piața XAUUSD...")
    
    for symbol, settings in PAIRS_CONFIG.items():
        data = await get_market_analysis(symbol, settings['risk'])
        if "error" in data:
            await message.answer(f"❌ **{settings['name']}**: Eroare date.")
            continue
            
        icon = "🟢" if data['signal'] == "Buy" else "🔴" if data['signal'] == "Sell" else "⚪"
        caption = (f"📊 **RAPORT {settings['name']}**\n"
                   f"💰 Preț: `{data['price']}`\n"
                   f"📈 RSI: `{data['rsi']}`\n"
                   f"📢 Status: {icon} **{data['signal']}**")
        
        photo_file = BufferedInputFile(data['chart'].read(), filename="status.png")
        await message.answer_photo(photo=photo_file, caption=caption, parse_mode="Markdown")
