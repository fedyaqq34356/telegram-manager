import asyncio
import json
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import (
    get_user_channels, get_active_subscription, add_scheduled_post
)
from services.telethon_manager import get_client, get_active_clients
from database.db import get_telethon_accounts
from locales import t
from keyboards.main_kb import (
    channels_keyboard, source_channel_for_parser_keyboard, parser_delay_keyboard
)

router = Router()

class ParserStates(StatesGroup):
    choosing_source = State()
    entering_source_link = State()
    choosing_delay = State()
    entering_custom_delay = State()
    choosing_target = State()
    entering_posts_limit = State()

@router.callback_query(F.data == "settings:posting_parser")
async def parser_start(callback: CallbackQuery, state: FSMContext, lang: str):
    sub = await get_active_subscription(callback.from_user.id)
    if not sub:
        await callback.answer("❌ Требуется подписка", show_alert=True)
        return
    await state.set_state(ParserStates.entering_source_link)
    await callback.message.answer(
        "📡 <b>Парсер постов</b>\n\n"
        "Введите @username или ссылку на канал-источник, откуда нужно скопировать посты:",
        parse_mode='HTML'
    )

@router.message(F.text.in_(["📋 Парсер постов", "📋 Post Parser"]))
async def parser_start_msg(message: Message, state: FSMContext, lang: str):
    sub = await get_active_subscription(message.from_user.id)
    if not sub:
        await message.answer("❌ Эта функция доступна только по подписке.")
        return
    await state.set_state(ParserStates.entering_source_link)
    await message.answer(
        "📡 <b>Парсер постов</b>\n\n"
        "Введите @username или ссылку на канал-источник:",
        parse_mode='HTML'
    )

@router.message(ParserStates.entering_source_link)
async def process_source_link(message: Message, state: FSMContext, lang: str):
    source = message.text.strip()
    if source.startswith("https://t.me/"):
        source = "@" + source.split("t.me/")[-1].split("/")[0]
    await state.update_data(parser_source=source)
    await state.set_state(ParserStates.entering_posts_limit)
    await message.answer("📊 Сколько последних постов скопировать? (1–100):")

@router.message(ParserStates.entering_posts_limit)
async def process_posts_limit(message: Message, state: FSMContext, lang: str):
    try:
        limit = int(message.text.strip())
        if not (1 <= limit <= 100):
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 1 до 100:")
        return
    await state.update_data(parser_limit=limit)
    await state.set_state(ParserStates.choosing_delay)
    await message.answer(
        "⏰ <b>Выберите задержку</b>\n\n"
        "На сколько сдвинуть каждый пост относительно его оригинального времени публикации?",
        reply_markup=parser_delay_keyboard(lang),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("parser_delay:"), ParserStates.choosing_delay)
async def parser_delay_chosen(callback: CallbackQuery, state: FSMContext, lang: str):
    value = callback.data.split(":")[1]
    if value == "custom":
        await state.set_state(ParserStates.entering_custom_delay)
        await callback.message.answer("✏️ Введите задержку в часах (например: 36):")
        return
    hours = int(value)
    await state.update_data(parser_delay_hours=hours)
    await _choose_target_channel(callback.message, state, lang, callback.from_user.id)

@router.message(ParserStates.entering_custom_delay)
async def process_custom_delay(message: Message, state: FSMContext, lang: str):
    try:
        hours = int(message.text.strip())
        if hours < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое число часов (минимум 1):")
        return
    await state.update_data(parser_delay_hours=hours)
    await _choose_target_channel(message, state, lang, message.from_user.id)

async def _choose_target_channel(message: Message, state: FSMContext, lang: str, user_id: int):
    channels = await get_user_channels(user_id)
    if not channels:
        await message.answer("❌ У вас нет добавленных каналов. Сначала добавьте канал.")
        await state.clear()
        return
    await state.set_state(ParserStates.choosing_target)
    await message.answer(
        "📤 <b>Выберите целевой канал</b>\n\nКуда публиковать скопированные посты:",
        reply_markup=channels_keyboard(lang, channels),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("channel:select:"), ParserStates.choosing_target)
async def parser_target_chosen(callback: CallbackQuery, state: FSMContext, lang: str, bot: Bot):
    target_channel_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    source = data['parser_source']
    delay_hours = data['parser_delay_hours']
    limit = data.get('parser_limit', 10)

    await state.clear()
    await callback.message.edit_text(
        f"⏳ <b>Парсинг запущен</b>\n\n"
        f"Источник: <code>{source}</code>\n"
        f"Постов: {limit}\n"
        f"Задержка: +{delay_hours} ч.\n\n"
        f"Получаю посты...",
        parse_mode='HTML'
    )

    accounts = await get_telethon_accounts()
    if not accounts:
        await callback.message.edit_text("❌ Нет подключённых Telethon-аккаунтов. Добавьте в админке.")
        return

    client = None
    for acc in accounts:
        try:
            client = await get_client(acc['name'], acc['api_id'], acc['api_hash'])
            break
        except Exception:
            continue

    if not client:
        await callback.message.edit_text("❌ Не удалось подключиться ни к одному аккаунту.")
        return

    try:
        entity = await client.get_entity(source)
    except Exception as e:
        await callback.message.edit_text(f"❌ Не удалось найти канал <code>{source}</code>: {e}", parse_mode='HTML')
        return

    saved = 0
    skipped = 0
    async for msg in client.iter_messages(entity, limit=limit):
        if not msg.date:
            skipped += 1
            continue

        original_time = msg.date.replace(tzinfo=None)
        scheduled_at = original_time + timedelta(hours=delay_hours)

        if scheduled_at < datetime.now():
            scheduled_at = datetime.now() + timedelta(hours=delay_hours)

        text = msg.message or ''
        media_type = None
        media_file_id = None

        if msg.photo:
            media_type = 'photo'
            try:
                sent = await bot.send_photo(callback.from_user.id, await _download_media(client, msg, bot))
                media_file_id = sent.photo[-1].file_id
                await bot.delete_message(callback.from_user.id, sent.message_id)
            except Exception:
                skipped += 1
                continue

        elif msg.video:
            media_type = 'video'
            try:
                sent = await bot.send_video(callback.from_user.id, await _download_media(client, msg, bot))
                media_file_id = sent.video.file_id
                await bot.delete_message(callback.from_user.id, sent.message_id)
            except Exception:
                skipped += 1
                continue

        buttons = []
        if msg.reply_markup:
            try:
                for row in msg.reply_markup.rows:
                    for btn in row.buttons:
                        if hasattr(btn, 'url') and btn.url:
                            buttons.append(f"{btn.text} | {btn.url}")
            except Exception:
                pass

        await add_scheduled_post(
            callback.from_user.id,
            target_channel_id,
            text,
            media_type,
            media_file_id,
            buttons,
            scheduled_at
        )
        saved += 1

    await callback.message.edit_text(
        f"✅ <b>Парсинг завершён!</b>\n\n"
        f"Сохранено постов: <b>{saved}</b>\n"
        f"Пропущено: {skipped}\n\n"
        f"Посты будут опубликованы автоматически с задержкой +{delay_hours} ч. от оригинальной даты.",
        parse_mode='HTML'
    )

async def _download_media(client, msg, bot: Bot) -> bytes:
    return await client.download_media(msg, bytes)