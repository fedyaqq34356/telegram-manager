import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

logger = logging.getLogger(__name__)

_dp: Dispatcher | None = None
_custom_bots: dict[str, Bot] = {}

ALLOWED_UPDATES = [
    "message", "edited_message", "channel_post", "edited_channel_post",
    "callback_query", "my_chat_member", "chat_member", "pre_checkout_query",
    "successful_payment"
]

def init(dp: Dispatcher):
    global _dp
    _dp = dp

async def _poll_bot(bot: Bot):
    offset = 0
    while True:
        try:
            updates = await bot.get_updates(offset=offset, timeout=30, allowed_updates=ALLOWED_UPDATES)
            for update in updates:
                await _dp.feed_update(bot, update)
                offset = update.update_id + 1
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Ошибка polling кастомного бота: {e}")
            await asyncio.sleep(5)

async def start_custom_bot(token: str) -> Bot:
    if token in _custom_bots:
        return _custom_bots[token]
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    _custom_bots[token] = bot
    asyncio.create_task(_poll_bot(bot))
    logger.info(f"Запущен кастомный бот {token[:10]}...")
    return bot

def get_bot_by_token(token: str) -> Bot | None:
    return _custom_bots.get(token)

async def get_bot_for_user(user_id: int) -> Bot | None:
    from database.db import get_user_custom_token
    token = await get_user_custom_token(user_id)
    if not token:
        return None
    return _custom_bots.get(token)

async def send_to_user(fallback_bot: Bot, user_id: int, text: str, **kwargs):
    bot = await get_bot_for_user(user_id) or fallback_bot
    return await bot.send_message(user_id, text, **kwargs)