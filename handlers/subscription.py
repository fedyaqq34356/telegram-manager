from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import (
    get_subscription_plans, get_active_subscription, create_payment,
    get_crypto_wallets, get_setting, update_payment_status, get_payment, create_subscription
)
from locales import t
from keyboards.main_kb import (
    plans_keyboard, period_keyboard, payment_method_keyboard,
    crypto_asset_keyboard, stars_channels_keyboard, check_crypto_keyboard
)

router = Router()

SUPPORTED_ASSETS = ["USDT", "TON", "BTC", "ETH", "LTC", "BNB", "TRX"]


class SubStates(StatesGroup):
    choosing_plan = State()
    choosing_period = State()
    choosing_payment = State()
    choosing_crypto_asset = State()
    choosing_stars_channels = State()


@router.message(F.text.in_(["💳 Купить подписку", "💳 Buy Subscription"]))
async def buy_sub_start(message: Message, state: FSMContext, lang: str):
    sub = await get_active_subscription(message.from_user.id)
    if sub:
        expires = sub["expires_at"][:16].replace("T", " ")
        await message.answer(
            t(lang, "sub_active", expires=expires, plan=sub["plan"]),
            parse_mode="HTML"
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
    plan = next((p for p in plans if p["id"] == plan_id), None)
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
    text = t(lang, "sub_info", plan=data["plan_name"], count=data["count"], months=months, price=price)
    await callback.message.edit_text(
        f"{text}\n\n{t(lang, 'choose_payment')}",
        reply_markup=payment_method_keyboard(lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "payment:crypto", SubStates.choosing_payment)
async def payment_crypto_chosen(callback: CallbackQuery, state: FSMContext, lang: str):
    from config import settings
    if not settings.CRYPTO_PAY_TOKEN:
        await callback.answer("❌ Крипто-оплата не настроена. Обратитесь к администратору.", show_alert=True)
        return
    await state.set_state(SubStates.choosing_crypto_asset)
    await callback.message.edit_text(
        "₿ <b>Выберите криптовалюту для оплаты:</b>",
        reply_markup=crypto_asset_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("crypto_asset:"), SubStates.choosing_crypto_asset)
async def crypto_asset_chosen(callback: CallbackQuery, state: FSMContext, lang: str):
    asset = callback.data.split(":")[1]
    data = await state.get_data()
    price_usd = data["price"]
    plan_name = data["plan_name"]
    months = data["months"]

    await callback.message.edit_text("⏳ Создаю счёт...")

    from services.crypto_pay import create_invoice
    invoice = await create_invoice(
        asset=asset,
        amount=price_usd,
        description=f"Подписка {plan_name} на {months} мес.",
        payload=f"sub_{callback.from_user.id}_{plan_name}_{months}"
    )

    if not invoice:
        await callback.message.edit_text(
            "❌ Не удалось создать счёт. Попробуйте позже или выберите другую валюту.",
            reply_markup=crypto_asset_keyboard()
        )
        return

    invoice_id = invoice["invoice_id"]
    pay_url = invoice["bot_invoice_url"]

    payment_id = await create_payment(
        callback.from_user.id, str(price_usd), asset,
        "crypto_auto", "main", plan_name, months
    )
    await update_payment_status(payment_id, "pending", str(invoice_id))

    await state.clear()

    await callback.message.edit_text(
        f"₿ <b>Счёт создан!</b>\n\n"
        f"Тариф: <b>{plan_name}</b> на {months} мес.\n"
        f"Сумма: <b>${price_usd} {asset}</b>\n\n"
        f"Нажмите кнопку ниже для оплаты через CryptoBot.\n"
        f"После оплаты подписка активируется <b>автоматически</b> в течение ~30 секунд.",
        reply_markup=check_crypto_keyboard(lang, pay_url, payment_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("crypto_check:"))
async def manual_check_crypto(callback: CallbackQuery, lang: str):
    payment_id = int(callback.data.split(":")[1])
    payment = await get_payment(payment_id)
    if not payment:
        await callback.answer("❌ Платёж не найден", show_alert=True)
        return
    if payment["status"] == "approved":
        await callback.answer("✅ Подписка уже активирована!", show_alert=True)
        return

    invoice_id = payment["tx_hash"]
    if not invoice_id:
        await callback.answer("❌ Ошибка: invoice не найден", show_alert=True)
        return

    from services.crypto_pay import check_invoice_paid
    paid = await check_invoice_paid(int(invoice_id))
    if paid:
        await update_payment_status(payment_id, "approved")
        await create_subscription(
            callback.from_user.id, "main", payment["plan"],
            5, 5, payment["months"]
        )
        await callback.message.edit_text(
            "✅ <b>Оплата подтверждена!</b>\n\nПодписка активирована.",
            parse_mode="HTML"
        )
    else:
        await callback.answer("⏳ Оплата ещё не поступила. Попробуйте через минуту.", show_alert=True)


@router.callback_query(F.data == "payment:stars", SubStates.choosing_payment)
async def payment_stars_chosen(callback: CallbackQuery, state: FSMContext, lang: str):
    price_per_channel = int(await get_setting("stars_per_channel", "100"))
    await state.set_state(SubStates.choosing_stars_channels)
    await callback.message.edit_text(
        f"⭐ <b>Выберите количество каналов</b>\n\n"
        f"Стоимость: {price_per_channel} ⭐ за канал",
        reply_markup=stars_channels_keyboard(lang, price_per_channel),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("stars_channels:"), SubStates.choosing_stars_channels)
async def stars_channels_chosen(callback: CallbackQuery, state: FSMContext, lang: str):
    parts = callback.data.split(":")
    channels_count = int(parts[1])
    stars_amount = int(parts[2])
    data = await state.get_data()
    plan_name = data.get("plan_name", "Подписка")
    months = data.get("months", 1)

    payment_id = await create_payment(
        callback.from_user.id, str(stars_amount), "XTR",
        "stars", "main", plan_name, months
    )
    await state.update_data(payment_id=payment_id, stars_channels_count=channels_count)
    await state.clear()

    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Подписка {plan_name}",
        description=f"{channels_count} канал(ов) на {months} мес.",
        payload=f"stars_{payment_id}_{channels_count}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan_name, amount=stars_amount)]
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    payload = message.successful_payment.invoice_payload
    parts = payload.split("_")
    if parts[0] != "stars" or len(parts) < 3:
        return
    payment_id = int(parts[1])
    channels_count = int(parts[2])

    payment = await get_payment(payment_id)
    if payment:
        await create_subscription(
            message.from_user.id, "main", payment["plan"],
            5, 5, payment["months"], channels_count
        )
        await update_payment_status(payment_id, "approved")

    await message.answer(
        f"✅ <b>Оплата прошла!</b>\n\nПодписка активирована.\nДоступно каналов: <b>{channels_count}</b>",
        parse_mode="HTML"
    )