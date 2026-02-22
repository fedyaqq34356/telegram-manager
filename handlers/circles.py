import asyncio
import os
import tempfile
import subprocess
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import (
    get_active_subscription, get_daily_usage, increment_daily_usage,
    get_setting, get_user_channels
)
from locales import t
from keyboards.main_kb import confirm_circle_keyboard, channels_keyboard

router = Router()

class CircleStates(StatesGroup):
    waiting_video = State()
    confirming = State()

async def convert_to_video_note(bot: Bot, file_id: str) -> bytes | None:
    try:
        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.mp4")
            output_path = os.path.join(tmpdir, "circle.mp4")

            dl_proc = await asyncio.create_subprocess_exec(
                "wget", "-q", "-O", input_path, file_url,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await dl_proc.wait()

            ffmpeg_proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-i", input_path,
                "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=384:384",
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac",
                "-t", "60",
                output_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await ffmpeg_proc.wait()

            if os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    return f.read()
    except Exception:
        pass
    return None

@router.callback_query(F.data == "settings:circles")
async def circles_menu(callback: CallbackQuery, state: FSMContext, lang: str):
    sub = await get_active_subscription(callback.from_user.id)
    usage = await get_daily_usage(callback.from_user.id, 'circles')
    free_limit = int(await get_setting('free_circles_per_day', '3'))

    if not sub and usage >= free_limit:
        await callback.answer(t(lang, "circle_limit"), show_alert=True)
        return

    await state.set_state(CircleStates.waiting_video)
    await callback.message.answer(t(lang, "send_video_circle"))

@router.message(CircleStates.waiting_video, F.video | F.video_note)
async def process_circle_video(message: Message, state: FSMContext, lang: str, bot: Bot):
    sub = await get_active_subscription(message.from_user.id)
    usage = await get_daily_usage(message.from_user.id, 'circles')
    free_limit = int(await get_setting('free_circles_per_day', '3'))

    if not sub and usage >= free_limit:
        await message.answer(t(lang, "circle_limit"))
        await state.clear()
        return

    processing_msg = await message.answer("⏳ Конвертирую видео в кружок...")

    if message.video_note:
        file_id = message.video_note.file_id
        await bot.delete_message(message.chat.id, processing_msg.message_id)
        sent = await message.answer_video_note(file_id)
    elif message.video:
        file_id = message.video.file_id
        video_bytes = await convert_to_video_note(bot, file_id)

        await bot.delete_message(message.chat.id, processing_msg.message_id)

        if video_bytes:
            sent = await message.answer_video_note(
                BufferedInputFile(video_bytes, filename="circle.mp4")
            )
            file_id = sent.video_note.file_id
        else:
            await message.answer("❌ Не удалось конвертировать видео. Убедитесь что ffmpeg установлен.")
            await state.clear()
            return

    await increment_daily_usage(message.from_user.id, 'circles')
    await state.update_data(circle_file_id=file_id)

    channels = await get_user_channels(message.from_user.id)
    if channels:
        await state.set_state(CircleStates.confirming)
        channel_id = channels[0]['channel_id']
        channel_title = channels[0]['channel_title'] or str(channel_id)
        await message.answer(
            f"✅ Кружок готов!\n\nОпубликовать в канале <b>{channel_title}</b>?",
            reply_markup=confirm_circle_keyboard(lang, channel_id),
            parse_mode='HTML'
        )
    else:
        await state.clear()
        await message.answer("✅ Готово!")

@router.callback_query(F.data.startswith("circle:send:"))
async def send_circle_to_channel(callback: CallbackQuery, state: FSMContext, lang: str, bot: Bot):
    channel_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    file_id = data.get('circle_file_id')

    try:
        await bot.send_video_note(channel_id, file_id)
        await callback.message.edit_text("✅ Кружок опубликован в канале!")
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка публикации: {e}")

    await state.clear()

@router.callback_query(F.data == "circle:skip")
async def skip_circle(callback: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await callback.message.edit_text("✅ Готово!")