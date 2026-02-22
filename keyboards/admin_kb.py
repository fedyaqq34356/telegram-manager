from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="📊 Статистика"),
        KeyboardButton(text="📨 Рассылка"),
        KeyboardButton(text="📤 Экспорт пользователей"),
        KeyboardButton(text="🎁 Выдать подписку"),
        KeyboardButton(text="👤 Кастомная подписка"),
        KeyboardButton(text="💳 Платежи (крипто)"),
        KeyboardButton(text="🤖 Аккаунты Telethon"),
        KeyboardButton(text="⚙️ Настройки бота"),
        KeyboardButton(text="📋 Тарифы"),
    )
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def approve_payment_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_pay:approve:{payment_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_pay:reject:{payment_id}"),
    )
    builder.adjust(2)
    return builder.as_markup()

def broadcast_filter_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="👥 Все пользователи", callback_data="broadcast:all"),
        InlineKeyboardButton(text="✅ С подпиской", callback_data="broadcast:has_sub"),
        InlineKeyboardButton(text="🆕 Пробовали демо", callback_data="broadcast:has_demo"),
        InlineKeyboardButton(text="🔴 Без демо", callback_data="broadcast:no_demo"),
        InlineKeyboardButton(text="🇷🇺 Русские", callback_data="broadcast:ru"),
        InlineKeyboardButton(text="🇺🇸 Английские", callback_data="broadcast:en"),
    )
    builder.adjust(2)
    return builder.as_markup()

def telethon_accounts_keyboard(accounts: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for acc in accounts:
        status = "✅" if acc['is_active'] else "❌"
        builder.add(InlineKeyboardButton(
            text=f"{status} {acc['name']} ({acc['phone']})",
            callback_data=f"telethon:remove:{acc['name']}"
        ))
    builder.add(InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="telethon:add"))
    builder.adjust(1)
    return builder.as_markup()

def grant_sub_period_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for months, label in [(1, "1 месяц"), (3, "3 месяца"), (6, "6 месяцев"), (12, "12 месяцев")]:
        builder.add(InlineKeyboardButton(text=label, callback_data=f"grant_period:{months}"))
    builder.adjust(2)
    return builder.as_markup()