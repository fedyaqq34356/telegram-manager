import io
import json
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import settings
from database.db import (
    get_stats, get_all_users, get_setting, set_setting,
    get_telethon_accounts, add_telethon_account, remove_telethon_account,
    get_crypto_wallets, add_crypto_wallet, remove_crypto_wallet,
    get_payment, update_payment_status, create_subscription,
    get_subscription_plans, get_pending_crypto_payments,
    get_user, get_users_with_subscription, get_users_without_demo,
    get_users_with_demo_no_sub, get_user_payment_total,
    create_custom_plan_for_user
)
from keyboards.admin_kb import (
    admin_menu_keyboard, approve_payment_keyboard,
    broadcast_filter_keyboard, telethon_accounts_keyboard,
    wallets_admin_keyboard, grant_sub_period_keyboard
)
from keyboards.main_kb import plans_keyboard

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS

class AdminStates(StatesGroup):
    broadcast_filter = State()
    broadcast_content = State()
    telethon_name = State()
    telethon_api_id = State()
    telethon_api_hash = State()
    telethon_phone = State()
    telethon_code = State()
    telethon_password = State()
    wallet_add_currency = State()
    wallet_add_address = State()
    grant_user_id = State()
    grant_plan = State()
    grant_period = State()
    setting_key = State()
    setting_value = State()
    custom_sub_user_id = State()
    custom_sub_plan_name = State()
    custom_sub_reactions = State()
    custom_sub_views = State()
    custom_sub_price = State()
    custom_sub_months = State()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🔧 Панель администратора", reply_markup=admin_menu_keyboard())

@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    stats = await get_stats()
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total']}</b>\n"
        f"🆕 Новых сегодня: <b>{stats['new_today']}</b>\n"
        f"📅 За неделю: <b>{stats['new_week']}</b>\n"
        f"🗓 За месяц: <b>{stats['new_month']}</b>\n\n"
        f"🌍 По языкам:\n"
        f"  🇷🇺 RU: {stats['ru_users']}\n"
        f"  🇺🇸 EN: {stats['en_users']}\n\n"
        f"🎯 Демо активировано: <b>{stats['demo_count']}</b>\n"
        f"💎 Платных подписок: <b>{stats['paid_count']}</b>\n\n"
        f"💳 Оплат криптой: {stats['crypto_pays']}\n"
        f"⭐ Оплат звёздами: {stats['stars_pays']}"
    )
    await message.answer(text, parse_mode='HTML')

@router.message(F.text == "📤 Экспорт пользователей")
async def export_users(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    users = await get_all_users()
    subs = await get_users_with_subscription()
    sub_ids = {u['tg_id'] for u in subs}

    lines = []
    for user in users:
        has_sub = "+" if user['tg_id'] in sub_ids else "-"
        earned = await get_user_payment_total(user['tg_id'])
        lines.append(f"{user['tg_id']}\t@{user['username'] or 'нет'}\t{user['full_name']}\t{has_sub}\t${earned:.2f}")

    content = "\n".join(lines).encode('utf-8')
    file = BufferedInputFile(content, filename="users.txt")
    await bot.send_document(message.chat.id, file, caption="📤 Экспорт пользователей")

@router.message(F.text == "📨 Рассылка")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.broadcast_filter)
    await message.answer("📨 Выберите аудиторию для рассылки:", reply_markup=broadcast_filter_keyboard())

@router.callback_query(F.data.startswith("broadcast:"), AdminStates.broadcast_filter)
async def broadcast_filter_chosen(callback: CallbackQuery, state: FSMContext):
    filter_type = callback.data.split(":")[1]
    await state.update_data(broadcast_filter=filter_type)
    await state.set_state(AdminStates.broadcast_content)
    await callback.message.edit_text(
        "📝 Отправьте сообщение для рассылки.\n\n"
        "Формат кнопок (после текста, через перенос):\n"
        "<code>Название кнопки | https://url.com</code>",
        parse_mode='HTML'
    )

@router.message(AdminStates.broadcast_content)
async def broadcast_content(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    filter_type = data.get('broadcast_filter', 'all')
    
    text = message.text or message.caption or ''
    buttons = []
    
    if text and '\n' in text:
        lines = text.split('\n')
        btn_lines = [l for l in lines if '|' in l and l.strip().startswith('http') == False]
        text_lines = [l for l in lines if '|' not in l or l.strip().startswith('http')]
        text = '\n'.join(text_lines).strip()
        buttons = btn_lines
    
    photo_id = None
    if message.photo:
        photo_id = message.photo[-1].file_id

    if filter_type == 'all':
        users = await get_all_users()
    elif filter_type == 'has_sub':
        users = await get_users_with_subscription()
    elif filter_type == 'has_demo':
        users = await get_users_with_demo_no_sub()
    elif filter_type == 'no_demo':
        users = await get_users_without_demo()
    elif filter_type == 'ru':
        all_users = await get_all_users()
        users = [u for u in all_users if u['language'] == 'ru']
    elif filter_type == 'en':
        all_users = await get_all_users()
        users = [u for u in all_users if u['language'] == 'en']
    else:
        users = await get_all_users()

    markup = None
    if buttons:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        builder = InlineKeyboardBuilder()
        for btn in buttons:
            if '|' in btn:
                parts = btn.split('|', 1)
                builder.add(InlineKeyboardButton(text=parts[0].strip(), url=parts[1].strip()))
        builder.adjust(1)
        markup = builder.as_markup()

    sent = 0
    failed = 0
    for user in users:
        try:
            if photo_id:
                await bot.send_photo(user['tg_id'], photo_id, caption=text, reply_markup=markup)
            else:
                await bot.send_message(user['tg_id'], text, reply_markup=markup)
            sent += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(f"✅ Рассылка завершена.\nОтправлено: {sent}\nОшибок: {failed}")

@router.message(F.text == "🎁 Выдать подписку")
async def grant_sub_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.grant_user_id)
    await message.answer("👤 Введите Telegram ID пользователя:")

@router.message(AdminStates.grant_user_id)
async def grant_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите числовой ID.")
        return
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return
    await state.update_data(grant_user_id=user_id)
    await state.set_state(AdminStates.grant_plan)
    plans = await get_subscription_plans()
    await message.answer("📋 Выберите тариф:", reply_markup=plans_keyboard('ru', plans))

@router.callback_query(F.data.startswith("plan:"), AdminStates.grant_plan)
async def grant_plan_chosen(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    plan_name = parts[2]
    count = int(parts[3])
    await state.update_data(grant_plan=plan_name, grant_count=count)
    await state.set_state(AdminStates.grant_period)
    await callback.message.edit_text("📅 Выберите период:", reply_markup=grant_sub_period_keyboard())

@router.callback_query(F.data.startswith("grant_period:"), AdminStates.grant_period)
async def grant_period_chosen(callback: CallbackQuery, state: FSMContext, bot: Bot):
    months = int(callback.data.split(":")[1])
    data = await state.get_data()
    user_id = data['grant_user_id']
    plan = data['grant_plan']
    count = data.get('grant_count', 5)

    await create_subscription(user_id, 'main', plan, count, count, months)
    await state.clear()
    await callback.message.edit_text(f"✅ Подписка выдана пользователю {user_id}")
    
    try:
        await bot.send_message(user_id, f"🎁 Вам выдана подписка {plan} на {months} мес.!")
    except Exception:
        pass

@router.message(F.text == "🤖 Аккаунты Telethon")
async def telethon_accounts_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    accounts = await get_telethon_accounts()
    await message.answer(
        f"🤖 Аккаунты Telethon ({len(accounts)} активных):\n\n"
        + "\n".join([f"• {a['name']} ({a['phone']})" for a in accounts] or ["Нет аккаунтов"]),
        reply_markup=telethon_accounts_keyboard(accounts)
    )

@router.callback_query(F.data == "telethon:add")
async def telethon_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.telethon_name)
    await callback.message.answer("📝 Введите имя сессии (например: acc1):")

@router.message(AdminStates.telethon_name)
async def telethon_add_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name.isidentifier():
        await message.answer("❌ Имя должно содержать только буквы, цифры и _")
        return
    await state.update_data(telethon_name=name)
    await state.set_state(AdminStates.telethon_api_id)
    await message.answer("🔑 Введите API ID (с my.telegram.org):")

@router.message(AdminStates.telethon_api_id)
async def telethon_add_api_id(message: Message, state: FSMContext):
    try:
        api_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ API ID должен быть числом.")
        return
    await state.update_data(telethon_api_id=api_id)
    await state.set_state(AdminStates.telethon_api_hash)
    await message.answer("🔐 Введите API Hash:")

@router.message(AdminStates.telethon_api_hash)
async def telethon_add_api_hash(message: Message, state: FSMContext):
    await state.update_data(telethon_api_hash=message.text.strip())
    await state.set_state(AdminStates.telethon_phone)
    await message.answer("📱 Введите номер телефона (формат: +79991234567):")

@router.message(AdminStates.telethon_phone)
async def telethon_add_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    data = await state.get_data()

    from services.telethon_manager import auth_start
    ok, result = await auth_start(
        message.from_user.id,
        data['telethon_name'],
        data['telethon_api_id'],
        data['telethon_api_hash'],
        phone
    )

    if ok:
        await state.set_state(AdminStates.telethon_code)
        await message.answer(f"✅ {result}\n\n📨 Введите код (можно через пробел, например: 1 2 3 4 5):")
    else:
        await state.clear()
        await message.answer(f"❌ Ошибка: {result}")

@router.message(AdminStates.telethon_code)
async def telethon_add_code(message: Message, state: FSMContext):
    code = message.text.replace(" ", "").strip()

    from services.telethon_manager import auth_verify_code, auth_cancel
    status, result = await auth_verify_code(message.from_user.id, code)

    if status == "2fa":
        await state.set_state(AdminStates.telethon_password)
        await message.answer(f"🔐 {result}")
    elif status == "retry":
        await message.answer(f"⚠️ {result}")
    elif status is True:
        await state.clear()
        await message.answer(f"✅ {result}")
    else:
        await auth_cancel(message.from_user.id)
        await state.clear()
        await message.answer(f"❌ Ошибка: {result}")

@router.message(AdminStates.telethon_password)
async def telethon_add_password(message: Message, state: FSMContext):
    from services.telethon_manager import auth_verify_password, auth_cancel
    ok, result = await auth_verify_password(message.from_user.id, message.text.strip())
    await state.clear()
    if ok:
        await message.answer(f"✅ {result}")
    else:
        await auth_cancel(message.from_user.id)
        await message.answer(f"❌ Ошибка: {result}")

@router.callback_query(F.data.startswith("telethon:remove:"))
async def telethon_remove(callback: CallbackQuery):
    name = callback.data.split(":", 2)[2]
    await remove_telethon_account(name)
    
    session_file = __import__('pathlib').Path(f"sessions/{name}.session")
    if session_file.exists():
        session_file.unlink()

    await callback.answer(f"✅ Аккаунт {name} удалён")
    accounts = await get_telethon_accounts()
    await callback.message.edit_reply_markup(reply_markup=telethon_accounts_keyboard(accounts))

@router.message(F.text == "💰 Крипто кошельки")
async def wallets_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    wallets = await get_crypto_wallets()
    await message.answer(
        f"💰 Крипто кошельки ({len(wallets)}):",
        reply_markup=wallets_admin_keyboard(wallets)
    )

@router.callback_query(F.data == "wallet:add")
async def wallet_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.wallet_add_currency)
    await callback.message.answer("💱 Введите название криптовалюты (например: USDT, BTC, TON):")

@router.message(AdminStates.wallet_add_currency)
async def wallet_add_currency(message: Message, state: FSMContext):
    await state.update_data(wallet_currency=message.text.strip().upper())
    await state.set_state(AdminStates.wallet_add_address)
    await message.answer("🏦 Введите адрес кошелька:")

@router.message(AdminStates.wallet_add_address)
async def wallet_add_address(message: Message, state: FSMContext):
    data = await state.get_data()
    await add_crypto_wallet(data['wallet_currency'], message.text.strip())
    await state.clear()
    await message.answer(f"✅ Кошелёк {data['wallet_currency']} добавлен!")

@router.callback_query(F.data.startswith("wallet:remove:"))
async def wallet_remove(callback: CallbackQuery):
    wallet_id = int(callback.data.split(":")[2])
    await remove_crypto_wallet(wallet_id)
    await callback.answer("✅ Кошелёк удалён")
    wallets = await get_crypto_wallets()
    await callback.message.edit_reply_markup(reply_markup=wallets_admin_keyboard(wallets))

@router.message(F.text == "💳 Платежи (крипто)")
async def pending_payments(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    payments = await get_pending_crypto_payments()
    if not payments:
        await message.answer("✅ Нет ожидающих платежей.")
        return
    for payment in payments:
        text = (
            f"💳 <b>Платёж #{payment['id']}</b>\n\n"
            f"👤 ID: <code>{payment['user_id']}</code>\n"
            f"💰 Сумма: {payment['amount']} {payment['currency']}\n"
            f"📋 Тариф: {payment['plan']}\n"
            f"📅 Период: {payment['months']} мес.\n"
            f"🔗 Хеш: <code>{payment['tx_hash'] or 'нет'}</code>"
        )
        await message.answer(text, reply_markup=approve_payment_keyboard(payment['id']), parse_mode='HTML')

@router.callback_query(F.data.startswith("admin_pay:"))
async def admin_payment_action(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    action = parts[1]
    payment_id = int(parts[2])
    
    payment = await get_payment(payment_id)
    if not payment:
        await callback.answer("❌ Платёж не найден", show_alert=True)
        return

    if action == "approve":
        await update_payment_status(payment_id, 'approved')
        await create_subscription(
            payment['user_id'], 'main', payment['plan'],
            5, 5, payment['months']
        )
        await callback.message.edit_text(f"✅ Платёж #{payment_id} подтверждён")
        try:
            user = await get_user(payment['user_id'])
            lang = user['language'] if user else 'ru'
            from locales import t
            await bot.send_message(payment['user_id'], t(lang, "payment_verified"))
        except Exception:
            pass
    elif action == "reject":
        await update_payment_status(payment_id, 'rejected')
        await callback.message.edit_text(f"❌ Платёж #{payment_id} отклонён")
        try:
            await bot.send_message(payment['user_id'], "❌ Ваш платёж был отклонён. Обратитесь в поддержку.")
        except Exception:
            pass

@router.message(F.text == "⚙️ Настройки бота")
async def bot_settings_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    keys = [
        'welcome_message', 'demo_duration_hours', 'free_circles_per_day',
        'free_posts_per_day', 'circles_sub_price', 'posts_sub_price',
        'full_sub_price', 'stars_per_channel'
    ]
    values = []
    for key in keys:
        val = await get_setting(key)
        values.append(f"<code>{key}</code> = {val}")
    
    await message.answer(
        "⚙️ <b>Настройки бота</b>\n\n" + "\n".join(values) +
        "\n\n📝 Введите: <code>ключ значение</code>",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.setting_key)

@router.message(AdminStates.setting_key)
async def process_setting(message: Message, state: FSMContext):
    parts = message.text.strip().split(' ', 1)
    if len(parts) != 2:
        await message.answer("❌ Формат: ключ значение")
        return
    key, value = parts
    await set_setting(key, value)
    await state.clear()
    await message.answer(f"✅ Настройка <code>{key}</code> = {value} сохранена!", parse_mode='HTML')

@router.message(F.text == "📋 Тарифы")
async def plans_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    plans = await get_subscription_plans()
    text = "📋 <b>Тарифы:</b>\n\n"
    for plan in plans:
        text += (
            f"<b>{plan['name']}</b>\n"
            f"  Реакций/просмотров: {plan['reactions_count']}\n"
            f"  1 мес: ${plan['price_1m']} | 3 мес: ${plan['price_3m']}\n"
            f"  6 мес: ${plan['price_6m']} | 12 мес: ${plan['price_12m']}\n\n"
        )
    await message.answer(text, parse_mode='HTML')

@router.message(F.text == "👤 Кастомная подписка")
async def custom_sub_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.custom_sub_user_id)
    await message.answer(
        "👤 <b>Кастомная подписка для пользователя</b>\n\n"
        "Введите Telegram ID пользователя:",
        parse_mode='HTML'
    )

@router.message(AdminStates.custom_sub_user_id)
async def custom_sub_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите числовой ID.")
        return
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Пользователь не найден в БД. Убедитесь, что он запускал бота.")
        return
    await state.update_data(custom_user_id=user_id)
    await state.set_state(AdminStates.custom_sub_plan_name)
    await message.answer(
        f"✅ Пользователь: <b>{user['full_name']}</b> (@{user['username'] or 'нет'})\n\n"
        f"Введите название тарифа (например: VIP, Премиум):",
        parse_mode='HTML'
    )

@router.message(AdminStates.custom_sub_plan_name)
async def custom_sub_plan_name(message: Message, state: FSMContext):
    await state.update_data(custom_plan_name=message.text.strip())
    await state.set_state(AdminStates.custom_sub_reactions)
    await message.answer("🎯 Введите количество реакций в сутки (например: 25):")

@router.message(AdminStates.custom_sub_reactions)
async def custom_sub_reactions(message: Message, state: FSMContext):
    try:
        count = int(message.text.strip())
        if count < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое положительное число:")
        return
    await state.update_data(custom_reactions=count)
    await state.set_state(AdminStates.custom_sub_views)
    await message.answer("👁 Введите количество просмотров (например: 25):")

@router.message(AdminStates.custom_sub_views)
async def custom_sub_views(message: Message, state: FSMContext):
    try:
        count = int(message.text.strip())
        if count < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое положительное число:")
        return
    await state.update_data(custom_views=count)
    await state.set_state(AdminStates.custom_sub_price)
    await message.answer("💰 Введите цену в $ (для записи в историю платежей, например: 0 — если бесплатно):")

@router.message(AdminStates.custom_sub_price)
async def custom_sub_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(',', '.'))
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную сумму (например: 9.99 или 0):")
        return
    await state.update_data(custom_price=price)
    await state.set_state(AdminStates.custom_sub_months)
    await message.answer("📅 Введите срок подписки в месяцах (1, 3, 6 или 12):")

@router.message(AdminStates.custom_sub_months)
async def custom_sub_months(message: Message, state: FSMContext, bot: Bot):
    try:
        months = int(message.text.strip())
        if months < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое число месяцев:")
        return

    data = await state.get_data()
    user_id = data['custom_user_id']
    plan_name = data['custom_plan_name']
    reactions = data['custom_reactions']
    views = data['custom_views']
    price = data['custom_price']

    await create_custom_plan_for_user(user_id, plan_name, reactions, views, price, months)
    await state.clear()

    user = await get_user(user_id)
    await message.answer(
        f"✅ <b>Кастомная подписка выдана!</b>\n\n"
        f"👤 {user['full_name']} (<code>{user_id}</code>)\n"
        f"📋 Тариф: <b>{plan_name}</b>\n"
        f"🎯 Реакций: {reactions} | Просмотров: {views}\n"
        f"📅 Срок: {months} мес.\n"
        f"💰 Цена: ${price}",
        parse_mode='HTML'
    )

    try:
        user_lang = user['language'] if user else 'ru'
        msg = (
            f"🎁 <b>Вам выдана кастомная подписка!</b>\n\n"
            f"📋 Тариф: <b>{plan_name}</b>\n"
            f"🎯 Реакций: {reactions} | Просмотров: {views}\n"
            f"📅 Срок: {months} мес."
        ) if user_lang == 'ru' else (
            f"🎁 <b>You have received a custom subscription!</b>\n\n"
            f"📋 Plan: <b>{plan_name}</b>\n"
            f"🎯 Reactions: {reactions} | Views: {views}\n"
            f"📅 Duration: {months} mo."
        )
        await bot.send_message(user_id, msg, parse_mode='HTML')
    except Exception:
        pass