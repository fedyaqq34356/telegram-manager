from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import (
    get_subscription_plans, get_active_subscription, create_payment,
    get_crypto_wallets, get_setting, update_payment_status, get_payment, create_subscription
)
from locales import t
from keyboards.main_kb import (
    plans_keyboard, period_keyboard, payment_method_keyboard,
    crypto_wallets_keyboard, check_payment_keyboard, stars_channels_keyboard
)

router = Router()

class SubStates(StatesGroup):
    choosing_plan = State()
    choosing_period = State()
    choosing_payment = State()
    choosing_stars_channels = State()
    waiting_tx_hash = State()

@router.message(F.text.in_(["💳 Купить подписку", "💳 Buy Subscription"]))
async def buy_sub_start(message: Message, state: FSMContext, lang: str):
    sub = await get_active_subscription(message.from_user.id)
    if sub:
        expires = sub['expires_at'][:16].replace('T', ' ')
        await message.answer(
            t(lang, "sub_active", expires=expires, plan=sub['plan']),
            parse_mode='HTML'
        )
        return
    plans = await get_subscription_plans()
    await state.set_state(SubStates.choosing_plan)
    await message.answer(t(lang, "choose_plan"), reply_markup=plans_keyboard(lang, plans))

@router.callback_query(F.data.startswith("plan:"), SubStates.choosing_plan)
async def plan_chosen(callback: CallbackQuery, state: FSMContext, lang: str):
    parts = callback.data.split(":")
    plan_id = int(parts[1])
    plan_name = parts[2]
    count = int(parts[3])
    plans = await get_subscription_plans()
    plan = next((p for p in plans if p['id'] == plan_id), None)
    if not plan:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    await state.update_data(plan_id=plan_id, plan_name=plan_name, count=count)
    await state.set_state(SubStates.choosing_period)
    await callback.message.edit_text(
        t(lang, "choose_period"),
        reply_markup=period_keyboard(lang, f"{plan_id}:{plan_name}:{count}", dict(plan))
    )

@router.callback_query(F.data.startswith("period:"), SubStates.choosing_period)
async def period_chosen(callback: CallbackQuery, state: FSMContext, lang: str):
    parts = callback.data.split(":")
    months = int(parts[-2])
    price = float(parts[-1])
    data = await state.get_data()
    await state.update_data(months=months, price=price)
    await state.set_state(SubStates.choosing_payment)
    text = t(lang, "sub_info", plan=data['plan_name'], count=data['count'], months=months, price=price)
    await callback.message.edit_text(
        f"{text}\n\n{t(lang, 'choose_payment')}",
        reply_markup=payment_method_keyboard(lang),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "payment:crypto", SubStates.choosing_payment)
async def payment_crypto_chosen(callback: CallbackQuery, state: FSMContext, lang: str):
    wallets = await get_crypto_wallets()
    if not wallets:
        await callback.answer("❌ Нет доступных кошельков для оплаты", show_alert=True)
        return
    await callback.message.edit_text(t(lang, "choose_crypto"), reply_markup=crypto_wallets_keyboard(wallets, prefix="pay_wallet"))

@router.callback_query(F.data.startswith("pay_wallet:"))
async def wallet_chosen(callback: CallbackQuery, state: FSMContext, lang: str):
    wallet_id = int(callback.data.split(":")[1])
    wallets = await get_crypto_wallets()
    wallet = next((w for w in wallets if w['id'] == wallet_id), None)
    if not wallet:
        await callback.answer("❌ Кошелёк не найден", show_alert=True)
        return
    data = await state.get_data()
    payment_id = await create_payment(
        callback.from_user.id, str(data['price']), wallet['currency'],
        'crypto_manual', 'main', data['plan_name'], data['months']
    )
    await state.update_data(payment_id=payment_id)
    await state.set_state(SubStates.waiting_tx_hash)
    await callback.message.edit_text(
        t(lang, "crypto_payment_info", currency=wallet['currency'], address=wallet['wallet_address'], amount=data['price']),
        parse_mode='HTML'
    )
    await callback.message.answer(t(lang, "send_tx_hash"))

@router.message(SubStates.waiting_tx_hash)
async def process_tx_hash(message: Message, state: FSMContext, lang: str):
    tx_hash = message.text.strip()
    data = await state.get_data()
    payment_id = data.get('payment_id')
    await update_payment_status(payment_id, 'pending_review', tx_hash)
    payment = await get_payment(payment_id)
    from config import settings
    for admin_id in settings.ADMIN_IDS:
        try:
            from keyboards.admin_kb import approve_payment_keyboard
            text = (
                f"💳 <b>Новый платёж</b>\n\n"
                f"👤 ID: <code>{message.from_user.id}</code>\n"
                f"📛 Username: @{message.from_user.username or 'нет'}\n"
                f"💬 Имя: {message.from_user.full_name}\n"
                f"💰 Сумма: {payment['amount']} {payment['currency']}\n"
                f"📋 Тариф: {payment['plan']}\n"
                f"📅 Период: {payment['months']} мес.\n"
                f"🔗 Хеш: <code>{tx_hash}</code>"
            )
            await message.bot.send_message(admin_id, text, reply_markup=approve_payment_keyboard(payment_id), parse_mode='HTML')
        except Exception:
            pass
    await state.clear()
    await message.answer(t(lang, "payment_sent_admin"))

@router.callback_query(F.data == "payment:stars", SubStates.choosing_payment)
async def payment_stars_chosen(callback: CallbackQuery, state: FSMContext, lang: str):
    price_per_channel = int(await get_setting('stars_per_channel', '100'))
    await state.set_state(SubStates.choosing_stars_channels)
    await callback.message.edit_text(
        f"⭐ <b>Выберите количество каналов</b>\n\n"
        f"Стоимость: {price_per_channel} ⭐ за канал\n\n"
        f"Реакции будут ставиться на посты в выбранном количестве ваших каналов одновременно.",
        reply_markup=stars_channels_keyboard(lang, price_per_channel),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("stars_channels:"), SubStates.choosing_stars_channels)
async def stars_channels_chosen(callback: CallbackQuery, state: FSMContext, lang: str):
    parts = callback.data.split(":")
    channels_count = int(parts[1])
    stars_amount = int(parts[2])
    data = await state.get_data()
    payment_id = await create_payment(
        callback.from_user.id, str(stars_amount), 'stars',
        'stars', 'main', data.get('plan_name', ''), data.get('months', 1)
    )
    await state.update_data(payment_id=payment_id, stars_channels_count=channels_count)
    from config import settings
    invite_link = settings.STARS_CHANNEL_INVITE
    await callback.message.edit_text(
        f"⭐ <b>Оплата звёздами</b>\n\n"
        f"Каналов: <b>{channels_count}</b>\n"
        f"Сумма: <b>{stars_amount} ⭐</b>\n\n"
        f"Подпишитесь на канал по ссылке:\n{invite_link}\n\n"
        f"После оплаты нажмите <b>«{t(lang, 'check_payment')}»</b>.",
        reply_markup=check_payment_keyboard(lang),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "payment:check")
async def check_stars_payment(callback: CallbackQuery, state: FSMContext, lang: str):
    from config import settings
    try:
        member = await callback.bot.get_chat_member(settings.STARS_CHANNEL_ID, callback.from_user.id)
        is_member = member.status not in ('left', 'kicked', 'banned')
    except Exception:
        is_member = False

    if is_member:
        data = await state.get_data()
        payment_id = data.get('payment_id')
        channels_count = data.get('stars_channels_count', 1)
        if payment_id:
            payment = await get_payment(payment_id)
            await create_subscription(
                callback.from_user.id, 'main', payment['plan'],
                5, 5, payment['months'], channels_count
            )
            await update_payment_status(payment_id, 'approved')
        try:
            await callback.bot.ban_chat_member(settings.STARS_CHANNEL_ID, callback.from_user.id)
            await callback.bot.unban_chat_member(settings.STARS_CHANNEL_ID, callback.from_user.id)
        except Exception:
            pass
        await state.clear()
        await callback.message.edit_text(
            f"✅ <b>Оплата подтверждена!</b>\n\nПодписка активирована.\nДоступно каналов: <b>{channels_count}</b>",
            parse_mode='HTML'
        )
    else:
        await callback.answer(t(lang, "payment_not_found"), show_alert=True)