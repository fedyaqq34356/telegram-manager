import json
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import (
    get_active_subscription, get_daily_usage, increment_daily_usage,
    get_setting, get_user_channels, add_scheduled_post
)
from locales import t
from keyboards.main_kb import (
    post_channel_keyboard, post_timing_keyboard, skip_keyboard
)

router = Router()

class PostStates(StatesGroup):
    selecting_channel = State()
    waiting_content = State()
    waiting_buttons = State()
    waiting_time = State()

@router.callback_query(F.data == "settings:posting")
async def posting_menu(callback: CallbackQuery, state: FSMContext, lang: str):
    sub = await get_active_subscription(callback.from_user.id)
    usage = await get_daily_usage(callback.from_user.id, 'posts')
    free_limit = int(await get_setting('free_posts_per_day', '3'))

    if not sub and usage >= free_limit:
        await callback.answer(t(lang, "post_limit"), show_alert=True)
        return

    channels = await get_user_channels(callback.from_user.id)
    if not channels:
        await callback.answer(t(lang, "no_channels"), show_alert=True)
        return

    await state.set_state(PostStates.selecting_channel)
    await callback.message.answer(
        t(lang, "select_channel"),
        reply_markup=post_channel_keyboard(channels)
    )

@router.callback_query(F.data.startswith("post_channel:"), PostStates.selecting_channel)
async def channel_for_post_selected(callback: CallbackQuery, state: FSMContext, lang: str):
    channel_id = int(callback.data.split(":")[1])
    await state.update_data(post_channel_id=channel_id)
    await state.set_state(PostStates.waiting_content)
    await callback.message.edit_text(t(lang, "post_content"))

@router.message(PostStates.waiting_content, F.photo | F.video | F.text)
async def process_post_content(message: Message, state: FSMContext, lang: str):
    media_type = None
    media_file_id = None
    text = None

    if message.photo:
        media_type = 'photo'
        media_file_id = message.photo[-1].file_id
        text = message.caption or ''
    elif message.video:
        media_type = 'video'
        media_file_id = message.video.file_id
        text = message.caption or ''
    else:
        text = message.text or ''

    await state.update_data(
        post_media_type=media_type,
        post_media_file_id=media_file_id,
        post_text=text
    )
    await state.set_state(PostStates.waiting_buttons)
    await message.answer(
        t(lang, "post_buttons"),
        reply_markup=skip_keyboard(lang, "post:skip_buttons"),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "post:skip_buttons", PostStates.waiting_buttons)
async def skip_buttons(callback: CallbackQuery, state: FSMContext, lang: str):
    await state.update_data(post_buttons=[])
    await state.set_state(PostStates.waiting_time)
    await callback.message.edit_text(
        t(lang, "post_schedule"),
        reply_markup=post_timing_keyboard(lang),
        parse_mode='HTML'
    )

@router.message(PostStates.waiting_buttons)
async def process_buttons(message: Message, state: FSMContext, lang: str):
    buttons = [line.strip() for line in message.text.strip().split('\n') if '|' in line]
    await state.update_data(post_buttons=buttons)
    await state.set_state(PostStates.waiting_time)
    await message.answer(
        t(lang, "post_schedule"),
        reply_markup=post_timing_keyboard(lang),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "post_time:now", PostStates.waiting_time)
async def post_now(callback: CallbackQuery, state: FSMContext, lang: str, bot: Bot):
    data = await state.get_data()
    await _send_post(callback.from_user.id, data, bot)
    await increment_daily_usage(callback.from_user.id, 'posts')
    await state.clear()
    await callback.message.edit_text(t(lang, "post_sent"))

@router.callback_query(F.data == "post_time:schedule", PostStates.waiting_time)
async def post_schedule_ask(callback: CallbackQuery, state: FSMContext, lang: str):
    await callback.message.edit_text("📅 Введите дату и время (формат: ДД.ММ.ГГГГ ЧЧ:ММ):")

@router.message(PostStates.waiting_time)
async def process_schedule_time(message: Message, state: FSMContext, lang: str):
    try:
        scheduled_at = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ")
        return

    data = await state.get_data()
    await add_scheduled_post(
        message.from_user.id,
        data['post_channel_id'],
        data.get('post_text', ''),
        data.get('post_media_type'),
        data.get('post_media_file_id'),
        data.get('post_buttons', []),
        scheduled_at
    )
    await increment_daily_usage(message.from_user.id, 'posts')
    await state.clear()
    await message.answer(t(lang, "post_scheduled", time=scheduled_at.strftime("%d.%m.%Y %H:%M")))

async def _send_post(user_id: int, data: dict, bot: Bot):
    channel_id = data['post_channel_id']
    text = data.get('post_text', '')
    media_type = data.get('post_media_type')
    media_file_id = data.get('post_media_file_id')
    buttons = data.get('post_buttons', [])

    markup = None
    if buttons:
        builder = InlineKeyboardBuilder()
        for btn in buttons:
            if '|' in btn:
                parts = btn.split('|', 1)
                builder.add(InlineKeyboardButton(text=parts[0].strip(), url=parts[1].strip()))
        builder.adjust(1)
        markup = builder.as_markup()

    if media_type == 'photo':
        await bot.send_photo(channel_id, media_file_id, caption=text, reply_markup=markup)
    elif media_type == 'video':
        await bot.send_video(channel_id, media_file_id, caption=text, reply_markup=markup)
    else:
        await bot.send_message(channel_id, text, reply_markup=markup)