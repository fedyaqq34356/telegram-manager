import asyncio
import json
import random
import logging
from aiogram import Bot
from database.db import get_all_active_reaction_settings, get_telethon_accounts
from services.telethon_manager import get_client

logger = logging.getLogger(__name__)


class ReactionWorker:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = True
        self._clients = []
        self._registered_channels = set()

    async def run(self):
        logger.info("ReactionWorker: запуск")
        await self._refresh()
        while self.running:
            try:
                await self._refresh()
            except Exception as e:
                logger.error(f"ReactionWorker error: {e}")
            await asyncio.sleep(60)

    async def _refresh(self):
        accounts = await get_telethon_accounts()
        if not accounts:
            logger.warning("ReactionWorker: нет активных аккаунтов Telethon")
            return

        new_clients = []
        for acc in accounts:
            try:
                client = await get_client(acc["name"], acc["api_id"], acc["api_hash"])
                new_clients.append(client)
                logger.info(f"ReactionWorker: аккаунт {acc['name']} ({acc['phone']}) подключен")
            except Exception as e:
                logger.warning(f"ReactionWorker: не удалось подключить {acc['phone']}: {e}")

        self._clients = new_clients

        if not self._clients:
            logger.warning("ReactionWorker: нет подключённых клиентов, реакции не будут ставиться")
            return

        settings_list = await get_all_active_reaction_settings()
        if not settings_list:
            logger.info("ReactionWorker: нет активных настроек реакций")
            return

        for setting in settings_list:
            channel_id = setting["channel_id"]
            if channel_id in self._registered_channels:
                continue
            self._registered_channels.add(channel_id)
            reactions = json.loads(setting["reactions"])
            interval = setting["interval_minutes"]
            logger.info(f"ReactionWorker: регистрирую обработчик для канала {channel_id}, реакции: {reactions}, интервал: {interval} мин.")
            self._register_handler(channel_id, reactions, interval)

        for client in self._clients:
            if not client.is_connected():
                asyncio.create_task(client.run_until_disconnected())

        logger.info(f"ReactionWorker: слежу за {len(self._registered_channels)} каналами, клиентов: {len(self._clients)}")

    def _register_handler(self, channel_id: int, reactions: list, interval: int):
        from telethon import events

        clients_snapshot = list(self._clients)

        for client in clients_snapshot:
            @client.on(events.NewMessage(chats=channel_id))
            async def handler(event, _r=reactions, _i=interval, _c=clients_snapshot, _ch=channel_id):
                logger.info(f"ReactionWorker: новый пост в канале {_ch}, msg_id={event.message.id}, жду {_i} мин.")
                await asyncio.sleep(_i * 60)

                chosen = random.sample(_c, min(len(_c), 3))
                logger.info(f"ReactionWorker: ставлю реакции на msg_id={event.message.id}, аккаунтов: {len(chosen)}")

                for c in chosen:
                    reaction = random.choice(_r)
                    try:
                        from telethon.tl.functions.messages import SendReactionRequest
                        from telethon.tl.types import ReactionEmoji
                        await c(SendReactionRequest(
                            peer=event.chat_id,
                            msg_id=event.message.id,
                            reaction=[ReactionEmoji(emoticon=reaction)]
                        ))
                        logger.info(f"ReactionWorker: реакция {reaction} поставлена на msg_id={event.message.id} в канале {_ch}")
                        await asyncio.sleep(random.uniform(1, 5))
                    except Exception as e:
                        logger.warning(f"ReactionWorker: ошибка реакции {reaction} на msg_id={event.message.id}: {e}")

    def stop(self):
        self.running = False
        logger.info("ReactionWorker: остановлен")