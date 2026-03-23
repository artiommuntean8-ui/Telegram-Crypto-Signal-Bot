# handlers.py
import aiohttp
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from database import add_user, deactivate_user, extend_subscription, get_active_users
from market_data import get_market_analysis
from config import ALLOWED_USERS, PAIRS_CONFIG, LEMONSQUEEZY_API_KEY, LEMONSQUEEZY_STORE_ID

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
    if not LEMONSQUEEZY_API_KEY:
        await message.answer("⚠️ Sistemul de plăți este momentan dezactivat.")
        return

    await message.answer("👇 **Alege planul potrivit pentru tine:**")

    # Definim produsele (Variant ID se ia din Dashboard-ul Lemon Squeezy)
    # Exemplu: Products -> click pe produs -> Copy Variant ID
    products = [
        {"name": "Săptămânal", "variant_id": "11111", "price_display": "15$"},
        {"name": "Lunar", "variant_id": "22222", "price_display": "45$"},
        {"name": "Anual", "variant_id": "33333", "price_display": "400$"},
    ]

    keyboard = []
    
    async with aiohttp.ClientSession() as session:
        headers = {
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
            "Authorization": f"Bearer {LEMONSQUEEZY_API_KEY}"
        }
        
        for prod in products:
            # Structura JSON API pentru Lemon Squeezy
            payload = {
                "data": {
                    "type": "checkouts",
                    "attributes": {
                        "checkout_data": {
                            "custom": {
                                "user_id": str(message.from_user.id),
                                "plan_name": prod['name']
                            }
                        }
                    },
                    "relationships": {
                        "store": {"data": {"type": "stores", "id": str(LEMONSQUEEZY_STORE_ID)}},
                        "variant": {"data": {"type": "variants", "id": str(prod['variant_id'])}}
                    }
                }
            }

            try:
                async with session.post("https://api.lemonsqueezy.com/v1/checkouts", json=payload, headers=headers) as resp:
                    if resp.status == 201:
                        data = await resp.json()
                        checkout_url = data['data']['attributes']['url']
                        keyboard.append([InlineKeyboardButton(text=f"💳 {prod['name']} - {prod['price_display']}", url=checkout_url)])
                    else:
                        print(f"Eroare LS: {await resp.text()}")
            except Exception as e:
                print(f"Eroare API: {e}")

    await message.answer("Alege opțiunea de plată:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

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
