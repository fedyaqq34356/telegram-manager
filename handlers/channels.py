import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER, ADMINISTRATOR
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import (
    add_user_channel, get_user_channels, remove_user_channel,
    get_channel, get_telethon_accounts,
    set_user_custom_token, get_user_custom_token
)
from locales import t
from keyboards.main_kb import (
    done_keyboard, channels_keyboard, channel_actions_keyboard,
    method_keyboard
)

router = Router()

class ChannelStates(StatesGroup):
    waiting_method = State()
    waiting_token = State()
    waiting_channel_added = State()
    waiting_accounts_added = State()

@router.message(F.text.in_(["🚀 Запустить", "🚀 Launch"]))
async def launch_handler(message: Message, lang: str):
    from keyboards.main_kb import launch_keyboard
    await message.answer(t(lang, "main_menu"), reply_markup=launch_keyboard(lang))

@router.callback_query(F.data == "channel:add")
async def add_channel_start(callback: CallbackQuery, state: FSMContext, lang: str):
    await state.set_state(ChannelStates.waiting_method)
    await callback.message.answer(
        t(lang, "choose_method"),
        reply_markup=method_keyboard(lang)
    )

@router.callback_query(F.data == "method:1")
async def method_1_chosen(callback: CallbackQuery, state: FSMContext, lang: str, bot: Bot):
    await state.update_data(method=1)
    await state.set_state(ChannelStates.waiting_channel_added)
    bot_me = await bot.get_me()
    await callback.message.answer(
        t(lang, "method_1_instruction", bot_username=bot_me.username),
        reply_markup=done_keyboard(lang, "channel:done_add"),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "method:2")
async def method_2_chosen(callback: CallbackQuery, state: FSMContext, lang: str):
    await state.update_data(method=2)
    await state.set_state(ChannelStates.waiting_token)
    await callback.message.answer(t(lang, "send_bot_token"))

@router.message(ChannelStates.waiting_token)
async def process_bot_token(message: Message, state: FSMContext, lang: str, bot: Bot):
    token = message.text.strip()
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.telegram.org/bot{token}/getMe") as resp:
                data = await resp.json()
                if not data.get('ok'):
                    await message.answer(t(lang, "invalid_token"))
                    return
                custom_bot_username = data['result']['username']
    except Exception:
        await message.answer(t(lang, "invalid_token"))
        return

    await set_user_custom_token(message.from_user.id, token)

    from services import user_bot as user_bot_service
    await user_bot_service.start_custom_bot(token)

    await state.update_data(custom_token=token, custom_bot_username=custom_bot_username)
    await state.set_state(ChannelStates.waiting_channel_added)
    await message.answer(
        t(lang, "token_accepted", bot_username=custom_bot_username),
        reply_markup=done_keyboard(lang, "channel:done_add"),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "channel:done_add")
async def channel_done_add(callback: CallbackQuery, state: FSMContext, lang: str):
    accounts = await get_telethon_accounts()

    if not accounts:
        await callback.message.answer(
            "✅ Канал добавлен!\n\n"
            "⚠️ <b>Внимание:</b> У вас нет подключённых рабочих аккаунтов для простановки реакций.\n"
            "Попросите администратора добавить аккаунты через админ-панель.\n\n"
            "Введите /ready для продолжения.",
            parse_mode='HTML'
        )
        await state.clear()
        return

    account_list = "\n".join([f"• {acc['name']} ({acc['phone']})" for acc in accounts])
    await state.set_state(ChannelStates.waiting_accounts_added)
    await callback.message.answer(
        t(lang, "bot_added", accounts=account_list),
        reply_markup=done_keyboard(lang, "channel:accounts_done"),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "channel:accounts_done")
async def accounts_done(callback: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await callback.message.answer(t(lang, "all_set"))

@router.my_chat_member()
async def bot_added_to_channel(event: ChatMemberUpdated, bot: Bot):
    if event.new_chat_member.status in ('administrator', 'creator'):
        if event.chat.type in ('channel', 'supergroup'):
            user_id = event.from_user.id
            channel_id = event.chat.id
            channel_title = event.chat.title or ''
            channel_username = event.chat.username or ''
            custom_token = await get_user_custom_token(user_id)
            await add_user_channel(user_id, channel_id, channel_title, channel_username, custom_token)

@router.callback_query(F.data == "channel:list")
async def channels_list(callback: CallbackQuery, lang: str):
    channels = await get_user_channels(callback.from_user.id)
    if not channels:
        await callback.answer(t(lang, "no_channels"), show_alert=True)
        return
    await callback.message.edit_text(
        t(lang, "select_channel"),
        reply_markup=channels_keyboard(lang, channels)
    )

@router.callback_query(F.data.startswith("channel:select:"))
async def channel_selected(callback: CallbackQuery, lang: str):
    channel_id = int(callback.data.split(":")[2])
    ch = await get_channel(callback.from_user.id, channel_id)
    if not ch:
        await callback.answer(t(lang, "no_channels"), show_alert=True)
        return
    title = ch['channel_title'] or ch['channel_username'] or str(channel_id)
    await callback.message.edit_text(
        f"📡 <b>{title}</b>",
        reply_markup=channel_actions_keyboard(lang, channel_id),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("channel:remove:"))
async def remove_channel(callback: CallbackQuery, lang: str):
    channel_id = int(callback.data.split(":")[2])
    await remove_user_channel(callback.from_user.id, channel_id)
    await callback.answer(t(lang, "channel_removed"))
    channels = await get_user_channels(callback.from_user.id)
    await callback.message.edit_text(
        t(lang, "select_channel"),
        reply_markup=channels_keyboard(lang, channels)
    )