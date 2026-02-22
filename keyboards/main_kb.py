from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from locales import t

ALL_REACTIONS = ["👍", "❤️", "🔥", "🎉", "😁", "💯", "❤️‍🔥", "🥰", "👏", "🤩", "😱", "🤣", "😢", "👀", "🤔", "🤯", "😍", "🙏", "🤝", "💪"]

def lang_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇺🇸 English", callback_data="lang:en")
    )
    builder.adjust(2)
    return builder.as_markup()

def method_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t(lang, "method_1"), callback_data="method:1"),
        InlineKeyboardButton(text=t(lang, "method_2"), callback_data="method:2")
    )
    builder.adjust(1)
    return builder.as_markup()

def done_keyboard(lang: str, callback: str = "done") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "done"), callback_data=callback))
    return builder.as_markup()

def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text=t(lang, "launch")),
        KeyboardButton(text=t(lang, "buy_sub")),
        KeyboardButton(text=t(lang, "settings_btn")),
    )
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def launch_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t(lang, "configure_reactions"), callback_data="reactions:configure"),
        InlineKeyboardButton(text=t(lang, "add_channel"), callback_data="channel:add"),
        InlineKeyboardButton(text=t(lang, "start_worker"), callback_data="worker:start"),
        InlineKeyboardButton(text=t(lang, "stop_worker"), callback_data="worker:stop"),
    )
    builder.adjust(1)
    return builder.as_markup()

def settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t(lang, "language_btn"), callback_data="settings:language"),
        InlineKeyboardButton(text=t(lang, "circles_btn"), callback_data="settings:circles"),
        InlineKeyboardButton(text=t(lang, "posting_btn"), callback_data="settings:posting"),
        InlineKeyboardButton(text="📋 Парсер постов", callback_data="settings:posting_parser"),
    )
    builder.adjust(1)
    return builder.as_markup()

def reactions_keyboard(lang: str, selected: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for reaction in ALL_REACTIONS:
        mark = "✅" if reaction in selected else ""
        builder.add(InlineKeyboardButton(
            text=f"{mark}{reaction}",
            callback_data=f"reaction_toggle:{reaction}"
        ))
    builder.add(InlineKeyboardButton(text=t(lang, "done"), callback_data="reactions:save"))
    builder.adjust(5, 5, 5, 5, 1)
    return builder.as_markup()

def channels_keyboard(lang: str, channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.add(InlineKeyboardButton(
            text=f"📡 {ch['channel_title'] or ch['channel_username'] or ch['channel_id']}",
            callback_data=f"channel:select:{ch['channel_id']}"
        ))
    builder.add(InlineKeyboardButton(text=t(lang, "add_channel"), callback_data="channel:add"))
    builder.adjust(1)
    return builder.as_markup()

def channel_actions_keyboard(lang: str, channel_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t(lang, "configure_reactions"), callback_data=f"reactions:config:{channel_id}"),
        InlineKeyboardButton(text=t(lang, "remove_channel"), callback_data=f"channel:remove:{channel_id}"),
        InlineKeyboardButton(text=t(lang, "back"), callback_data="channel:list"),
    )
    builder.adjust(1)
    return builder.as_markup()

def plans_keyboard(lang: str, plans: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for plan in plans:
        builder.add(InlineKeyboardButton(
            text=f"💎 {plan['name']} ({plan['reactions_count']} реакций)",
            callback_data=f"plan:{plan['id']}:{plan['name']}:{plan['reactions_count']}"
        ))
    builder.adjust(1)
    return builder.as_markup()

def period_keyboard(lang: str, plan_data: str, prices: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    periods = [
        (1, t(lang, "months_1"), prices.get('price_1m', 0)),
        (3, t(lang, "months_3"), prices.get('price_3m', 0)),
        (6, t(lang, "months_6"), prices.get('price_6m', 0)),
        (12, t(lang, "months_12"), prices.get('price_12m', 0)),
    ]
    for months, label, price in periods:
        builder.add(InlineKeyboardButton(
            text=f"{label} — ${price}",
            callback_data=f"period:{plan_data}:{months}:{price}"
        ))
    builder.adjust(1)
    return builder.as_markup()

def payment_method_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t(lang, "pay_crypto"), callback_data="payment:crypto"),
        InlineKeyboardButton(text=t(lang, "pay_stars"), callback_data="payment:stars"),
    )
    builder.adjust(1)
    return builder.as_markup()

def crypto_wallets_keyboard(wallets: list, prefix: str = "wallet") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for w in wallets:
        builder.add(InlineKeyboardButton(
            text=f"💰 {w['currency']}",
            callback_data=f"{prefix}:{w['id']}"
        ))
    builder.adjust(2)
    return builder.as_markup()

def check_payment_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "check_payment"), callback_data="payment:check"))
    return builder.as_markup()

def post_channel_keyboard(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.add(InlineKeyboardButton(
            text=f"📡 {ch['channel_title'] or ch['channel_id']}",
            callback_data=f"post_channel:{ch['channel_id']}"
        ))
    builder.adjust(1)
    return builder.as_markup()

def post_timing_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t(lang, "post_now"), callback_data="post_time:now"),
        InlineKeyboardButton(text="🕐 Запланировать", callback_data="post_time:schedule"),
    )
    builder.adjust(1)
    return builder.as_markup()

def skip_keyboard(lang: str, callback: str = "skip") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "skip"), callback_data=callback))
    return builder.as_markup()

def confirm_circle_keyboard(lang: str, channel_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Отправить в канал", callback_data=f"circle:send:{channel_id}"),
        InlineKeyboardButton(text="❌ Не отправлять", callback_data="circle:skip"),
    )
    builder.adjust(1)
    return builder.as_markup()

def stars_channels_keyboard(lang: str, price_per_channel: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    options = [
        (1, f"1 канал — {price_per_channel} ⭐"),
        (3, f"3 канала — {price_per_channel * 3} ⭐"),
        (5, f"5 каналов — {price_per_channel * 5} ⭐"),
    ]
    for count, label in options:
        builder.add(InlineKeyboardButton(
            text=label,
            callback_data=f"stars_channels:{count}:{price_per_channel * count}"
        ))
    builder.adjust(1)
    return builder.as_markup()

def source_channel_for_parser_keyboard(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.add(InlineKeyboardButton(
            text=f"📡 {ch['channel_title'] or ch['channel_username'] or ch['channel_id']}",
            callback_data=f"parser_src:{ch['channel_id']}"
        ))
    builder.adjust(1)
    return builder.as_markup()

def parser_delay_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    delays = [
        (24, "⏰ +1 день"),
        (48, "⏰ +2 дня"),
        (72, "⏰ +3 дня"),
        (168, "⏰ +1 неделя"),
    ]
    for hours, label in delays:
        builder.add(InlineKeyboardButton(text=label, callback_data=f"parser_delay:{hours}"))
    builder.add(InlineKeyboardButton(text="✏️ Своё время (часы)", callback_data="parser_delay:custom"))
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def crypto_asset_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    assets = [
        ("USDT", "💵 USDT"),
        ("TON", "💎 TON"),
        ("BTC", "₿ BTC"),
        ("ETH", "⟠ ETH"),
        ("LTC", "Ł LTC"),
        ("BNB", "🔶 BNB"),
        ("TRX", "⚡ TRX"),
    ]
    for code, label in assets:
        builder.add(InlineKeyboardButton(text=label, callback_data=f"crypto_asset:{code}"))
    builder.adjust(3)
    return builder.as_markup()


def check_crypto_keyboard(lang: str, pay_url: str, payment_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💳 Оплатить через CryptoBot", url=pay_url),
        InlineKeyboardButton(text="🔍 Проверить оплату", callback_data=f"crypto_check:{payment_id}"),
    )
    builder.adjust(1)
    return builder.as_markup()