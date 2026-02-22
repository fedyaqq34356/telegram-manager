import asyncio
import json
import random
import logging
from datetime import datetime
from aiogram import Bot
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from config import settings
from database.db import get_all_active_reaction_settings, get_telethon_accounts

logger = logging.getLogger(__name__)

class ReactionWorker:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = True
        self._channel_listeners: dict[int, list] = {}
        self._clients: list[TelegramClient] = []

    async def run(self):
        while self.running:
            try:
                await self._refresh_listeners()
            except Exception as e:
                logger.error(f"ReactionWorker error: {e}")
            await asyncio.sleep(60)

    async def _refresh_listeners(self):
        settings_list = await get_all_active_reaction_settings()
        accounts = await get_telethon_accounts()

        for client in self._clients:
            if client.is_connected():
                await client.disconnect()
        self._clients.clear()

        for acc in accounts:
            try:
                client = TelegramClient(StringSession(acc['session_string']), settings.TG_API_ID, settings.TG_API_HASH)
                await client.connect()
                if await client.is_user_authorized():
                    self._clients.append(client)
            except Exception as e:
                logger.warning(f"Could not connect account {acc['phone']}: {e}")

        for setting in settings_list:
            channel_id = setting['channel_id']
            reactions = json.loads(setting['reactions'])
            interval = setting['interval_minutes']

            if not reactions or not self._clients:
                continue

            for client in self._clients:
                try:
                    @client.on(events.NewMessage(chats=channel_id))
                    async def handler(event, _reactions=reactions, _interval=interval, _clients=self._clients):
                        await asyncio.sleep(_interval * 60)
                        chosen_clients = random.sample(_clients, min(len(_clients), 3))
                        for c in chosen_clients:
                            reaction = random.choice(_reactions)
                            try:
                                from telethon.tl.functions.messages import SendReactionRequest
                                from telethon.tl.types import ReactionEmoji
                                await c(SendReactionRequest(
                                    peer=event.chat_id,
                                    msg_id=event.message.id,
                                    reaction=[ReactionEmoji(emoticon=reaction)]
                                ))
                                await asyncio.sleep(random.uniform(1, 5))
                            except Exception as e:
                                logger.warning(f"Reaction error: {e}")

                    if not client.is_connected():
                        await client.connect()
                except Exception as e:
                    logger.warning(f"Could not setup handler for channel {channel_id}: {e}")

        for client in self._clients:
            if not client.is_running():
                asyncio.create_task(client.run_until_disconnected())

    def stop(self):
        self.running = False