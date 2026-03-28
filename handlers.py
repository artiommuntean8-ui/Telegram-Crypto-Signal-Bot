# handlers.py
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from database import add_user, deactivate_user, extend_subscription, get_active_users
from market_data import get_market_analysis, is_market_open
from config import ALLOWED_USERS, PAIRS_CONFIG, TON_WALLET_ADDRESS, TON_PRODUCTS, ADMIN_LINK

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
    
    keyboard = []
    for code, details in TON_PRODUCTS.items():
        # Creăm buton pentru fiecare produs definit în config
        btn_text = f"{details['name']} - {details['price_usd']}$ ({details['price_ton']} TON)"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"buy_{code}")])

    await message.answer(
        "💎 **Plată prin TON Coin**\n"
        "Alege un pachet de mai jos. Vei fi redirecționat către portofelul tău TON pentru a efectua plata.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("buy_"))
async def process_buy_callback(callback: types.CallbackQuery):
    """Generează link-ul de plată TON și instrucțiunile."""
    product_code = callback.data.split("_")[1]
    
    if product_code not in TON_PRODUCTS:
        await callback.answer("Produs invalid.", show_alert=True)
        return

    if not TON_WALLET_ADDRESS or TON_WALLET_ADDRESS == "None":
        await callback.answer("⚠️ Eroare: Adresa portofelului nu este configurată în bot!", show_alert=True)
        return

    product = TON_PRODUCTS[product_code]
    
    # 1. Calculăm suma în Nanotons (1 TON = 1,000,000,000 nanotons)
    amount_nanotons = int(product['price_ton'] * 1_000_000_000)
    
    # 2. Generăm link-ul HTTP pentru Tonhub (mai compatibil)
    # Adăugăm un comentariu unic pentru a putea identifica plata manual (ex: UserID)
    comment = f"Sub_{callback.from_user.id}_{product_code}"
    payment_url = f"https://tonhub.com/transfer/{TON_WALLET_ADDRESS}?amount={amount_nanotons}&text={comment}"
    
    # 3. Construim tastatura cu butonul de plată
    keyboard = [
        [InlineKeyboardButton(text=f"🚀 Deschide Wallet ({product['price_ton']} TON)", url=payment_url)],
        [InlineKeyboardButton(text="📩 Trimite Dovada (Admin)", url=ADMIN_LINK)],
        [InlineKeyboardButton(text="🔙 Înapoi la planuri", callback_data="back_to_plans")]
    ]
    
    await callback.message.edit_text(
        f"🛒 **Confirmare Comandă**\n\n"
        f"📦 Pachet: **{product['name']}**\n"
        f"💰 Preț: **{product['price_usd']}$** (~{product['price_ton']} TON)\n\n"
        f"⚠️ **Instrucțiuni:**\n"
        f"1. Apasă butonul de mai jos pentru a deschide portofelul.\n"
        f"2. Confirmă tranzacția.\n"
        f"3. Trimite o captură de ecran administratorului pentru activare.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "back_to_plans")
async def process_back_to_plans(callback: types.CallbackQuery):
    """Revine la lista de planuri."""
    # Ștergem mesajul curent și re-apelăm comanda plans (prin editare)
    await callback.message.delete()
    await cmd_plans(callback.message)

@router.message(Command("activate"))
async def cmd_activate(message: types.Message):
    """
    Comandă pentru Admin: /activate <user_id> <zile>
    Exemplu: /activate 12345678 30
    """
    if message.from_user.id not in ALLOWED_USERS:
        return # Ignorăm dacă nu este admin

    args = message.text.split()
    if len(args) != 3:
        await message.answer("❌ Format incorect. Folosește: `/activate <user_id> <zile>`")
        return

    try:
        target_user_id = int(args[1])
        days = int(args[2])
        
        await extend_subscription(target_user_id, days)
        await message.answer(f"✅ Abonament activat pentru ID {target_user_id} timp de {days} zile.")
        
        # Notificăm și utilizatorul automat
        await message.bot.send_message(target_user_id, f"🎉 **Abonament Activat!**\nContul tău a fost creditat cu {days} zile de acces VIP. Spor la profit! 📈")
    except Exception as e:
        await message.answer(f"❌ Eroare la activare: {str(e)}")

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

    if not is_market_open():
        await message.answer("😴 **Piața este închisă momentan.**\nXAUUSD nu se tranzacționează în weekend sau între orele 23:00 - 00:00.")
        return

    await message.answer("🔍 Analizez piața XAUUSD...")
    
    for symbol, settings in PAIRS_CONFIG.items():
        data = await get_market_analysis(symbol, settings['risk'])
        if "error" in data:
            await message.answer(f"❌ **{settings['name']}**: {data['error']}")
            continue
            
        icon = "🟢" if data['signal'] == "Buy" else "🔴" if data['signal'] == "Sell" else "⚪"
        caption = (f"📊 **RAPORT {settings['name']}**\n"
                   f"💰 Preț: `{data['price']}`\n"
                   f"📈 RSI: `{data['rsi']}`\n"
                   f"📢 Status: {icon} **{data['signal']}**")
        
        photo_file = BufferedInputFile(data['chart'].read(), filename="status.png")
        await message.answer_photo(photo=photo_file, caption=caption, parse_mode="Markdown")
