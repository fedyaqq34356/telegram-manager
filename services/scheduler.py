import asyncio
import json
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db import get_pending_posts, mark_post_sent

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = True

    async def run(self):
        while self.running:
            try:
                await self._process_pending_posts()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(30)

    async def _process_pending_posts(self):
        posts = await get_pending_posts()
        for post in posts:
            try:
                buttons_data = json.loads(post['buttons'] or '[]')
                markup = None
                if buttons_data:
                    builder = InlineKeyboardBuilder()
                    for btn in buttons_data:
                        if '|' in btn:
                            parts = btn.split('|', 1)
                            name = parts[0].strip()
                            url = parts[1].strip()
                            builder.add(InlineKeyboardButton(text=name, url=url))
                    builder.adjust(1)
                    markup = builder.as_markup()

                if post['media_type'] == 'photo':
                    await self.bot.send_photo(
                        post['channel_id'], post['media_file_id'],
                        caption=post['text_content'], reply_markup=markup
                    )
                elif post['media_type'] == 'video':
                    await self.bot.send_video(
                        post['channel_id'], post['media_file_id'],
                        caption=post['text_content'], reply_markup=markup
                    )
                elif post['media_type'] == 'video_note':
                    await self.bot.send_video_note(post['channel_id'], post['media_file_id'])
                else:
                    await self.bot.send_message(
                        post['channel_id'], post['text_content'] or '',
                        reply_markup=markup
                    )

                await mark_post_sent(post['id'])
            except Exception as e:
                logger.error(f"Failed to send post {post['id']}: {e}")
                await mark_post_sent(post['id'])

    def stop(self):
        self.running = False