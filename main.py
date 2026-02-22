import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import settings
from database.db import init_db
from handlers import start, channels, reactions, subscription, circles, posting, admin, post_parser
from services.reaction_worker import ReactionWorker
from services.scheduler import Scheduler
from services.crypto_poller import CryptoPayPoller
from middlewares.language import LanguageMiddleware

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(LanguageMiddleware())

    dp.include_router(start.router)
    dp.include_router(channels.router)
    dp.include_router(reactions.router)
    dp.include_router(subscription.router)
    dp.include_router(circles.router)
    dp.include_router(posting.router)
    dp.include_router(post_parser.router)
    dp.include_router(admin.router)

    await init_db()

    reaction_worker = ReactionWorker(bot)
    scheduler = Scheduler(bot)
    crypto_poller = CryptoPayPoller(bot)

    await asyncio.gather(
        dp.start_polling(bot, drop_pending_updates=True),
        reaction_worker.run(),
        scheduler.run(),
        crypto_poller.run(),
    )

if __name__ == '__main__':
    asyncio.run(main())