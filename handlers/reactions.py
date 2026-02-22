import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import (
    get_user_channels, get_reaction_settings, upsert_reaction_settings_field,
    upsert_reaction_settings
)
from locales import t
from keyboards.main_kb import reactions_keyboard, channels_keyboard

router = Router()

class ReactionStates(StatesGroup):
    selecting_channel = State()
    selecting_reactions = State()
    setting_interval = State()

@router.callback_query(F.data == "reactions:configure")
async def configure_reactions_start(callback: CallbackQuery, state: FSMContext, lang: str):
    channels = await get_user_channels(callback.from_user.id)
    if not channels:
        await callback.answer(t(lang, "no_channels"), show_alert=True)
        return
    if len(channels) == 1:
        await state.update_data(reaction_channel_id=channels[0]['channel_id'])
        await _show_reactions(callback, state, lang, channels[0]['channel_id'])
    else:
        await state.set_state(ReactionStates.selecting_channel)
        await callback.message.edit_text(
            t(lang, "select_channel"),
            reply_markup=channels_keyboard(lang, channels)
        )

@router.callback_query(F.data.startswith("reactions:config:"))
async def configure_reactions_for_channel(callback: CallbackQuery, state: FSMContext, lang: str):
    channel_id = int(callback.data.split(":")[2])
    await state.update_data(reaction_channel_id=channel_id)
    await _show_reactions(callback, state, lang, channel_id)

async def _show_reactions(callback: CallbackQuery, state: FSMContext, lang: str, channel_id: int):
    await state.set_state(ReactionStates.selecting_reactions)
    settings = await get_reaction_settings(callback.from_user.id, channel_id)
    selected = json.loads(settings['reactions']) if settings else []
    await state.update_data(selected_reactions=selected)
    await callback.message.edit_text(
        t(lang, "choose_reactions", count=len(selected)),
        reply_markup=reactions_keyboard(lang, selected)
    )

@router.callback_query(F.data.startswith("reaction_toggle:"), ReactionStates.selecting_reactions)
async def toggle_reaction(callback: CallbackQuery, state: FSMContext, lang: str):
    reaction = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = data.get('selected_reactions', [])

    if reaction in selected:
        selected.remove(reaction)
    else:
        selected.append(reaction)

    await state.update_data(selected_reactions=selected)
    await callback.message.edit_text(
        t(lang, "choose_reactions", count=len(selected)),
        reply_markup=reactions_keyboard(lang, selected)
    )

@router.callback_query(F.data == "reactions:save", ReactionStates.selecting_reactions)
async def save_reactions(callback: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    selected = data.get('selected_reactions', [])
    channel_id = data.get('reaction_channel_id')

    if not selected:
        await callback.answer("❌ Выберите хотя бы одну реакцию!", show_alert=True)
        return

    await upsert_reaction_settings_field(callback.from_user.id, channel_id, reactions=selected)
    await state.set_state(ReactionStates.setting_interval)
    await callback.message.edit_text(t(lang, "reactions_saved"))

@router.message(ReactionStates.setting_interval)
async def set_interval(message: Message, state: FSMContext, lang: str):
    try:
        minutes = int(message.text.strip())
        if minutes < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое число минут (минимум 1).")
        return

    data = await state.get_data()
    channel_id = data.get('reaction_channel_id')
    selected = data.get('selected_reactions', [])

    await upsert_reaction_settings(
        message.from_user.id, channel_id,
        selected, minutes, True
    )
    await state.clear()
    await message.answer(t(lang, "interval_set", minutes=minutes), parse_mode='HTML')

@router.callback_query(F.data == "worker:start")
async def start_worker(callback: CallbackQuery, lang: str):
    channels = await get_user_channels(callback.from_user.id)
    if not channels:
        await callback.answer(t(lang, "no_channels"), show_alert=True)
        return
    for ch in channels:
        settings = await get_reaction_settings(callback.from_user.id, ch['channel_id'])
        if settings:
            await upsert_reaction_settings_field(
                callback.from_user.id, ch['channel_id'], is_active=1
            )
    await callback.answer(t(lang, "worker_started"), show_alert=True)

@router.callback_query(F.data == "worker:stop")
async def stop_worker(callback: CallbackQuery, lang: str):
    channels = await get_user_channels(callback.from_user.id)
    for ch in channels:
        await upsert_reaction_settings_field(
            callback.from_user.id, ch['channel_id'], is_active=0
        )
    await callback.answer(t(lang, "worker_stopped"), show_alert=True)