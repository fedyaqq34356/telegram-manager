from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import (
    get_user, create_user, update_user_language, activate_demo,
    get_setting, get_active_subscription
)
from locales import t
from keyboards.main_kb import lang_keyboard, main_menu_keyboard, method_keyboard

router = Router()

class SetupStates(StatesGroup):
    waiting_language = State()

@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, lang: str):
    from config import settings
    from keyboards.admin_kb import admin_menu_keyboard

    if message.from_user.id in settings.ADMIN_IDS:
        await message.answer("👑 Добро пожаловать в админ-панель!", reply_markup=admin_menu_keyboard())
        return

    user = await get_user(message.from_user.id)
    if not user:
        await create_user(
            message.from_user.id,
            message.from_user.username or '',
            message.from_user.full_name or ''
        )
    await state.set_state(SetupStates.waiting_language)
    await message.answer(
        "👋 Hello / Привет!\n\nPlease choose your language / Пожалуйста, выберите язык:",
        reply_markup=lang_keyboard()
    )

@router.callback_query(F.data.startswith("lang:"))
async def language_chosen(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split(":")[1]
    await update_user_language(callback.from_user.id, lang)
    await state.clear()

    welcome_msg = await get_setting('welcome_message', 'Добро пожаловать!')
    await callback.message.edit_text(t(lang, "language_set"))

    user = await get_user(callback.from_user.id)
    if not user['demo_activated']:
        demo_hours = int(await get_setting('demo_duration_hours', '24'))
        await activate_demo(callback.from_user.id, demo_hours)
        await callback.message.answer(
            f"{welcome_msg}\n\n{t(lang, 'demo_welcome')}",
            reply_markup=method_keyboard(lang),
            parse_mode='HTML'
        )
    else:
        sub = await get_active_subscription(callback.from_user.id)
        await callback.message.answer(
            welcome_msg,
            reply_markup=main_menu_keyboard(lang)
        )

@router.message(Command("ready"))
async def ready_handler(message: Message, lang: str):
    await message.answer(
        t(lang, "main_menu"),
        reply_markup=main_menu_keyboard(lang)
    )

@router.message(Command("language"))
async def change_language(message: Message):
    await message.answer(
        "Choose language / Выберите язык:",
        reply_markup=lang_keyboard()
    )

@router.message(F.text.in_(["⚙️ Настройки", "⚙️ Settings"]))
async def settings_handler(message: Message, lang: str):
    from keyboards.main_kb import settings_keyboard
    await message.answer(t(lang, "settings_btn"), reply_markup=settings_keyboard(lang))

@router.callback_query(F.data == "settings:language")
async def settings_language(callback: CallbackQuery):
    await callback.message.answer(
        "Choose language / Выберите язык:",
        reply_markup=lang_keyboard()
    )