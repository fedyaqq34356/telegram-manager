import asyncio
import json
import logging
import random
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.types import ReactionEmoji
from database.db import get_telethon_accounts, add_telethon_account

logger = logging.getLogger(__name__)

DEVICE_MODELS = [
    "Honor HONOR 70", "Samsung Galaxy S21", "Xiaomi Mi 11", "Google Pixel 6",
    "OnePlus 9", "Sony Xperia 5", "Huawei P50", "Nokia X20", "Motorola Edge 20",
    "Apple iPhone 13", "Apple iPhone 14", "Apple iPhone 15", "PC"
]

SYSTEM_VERSIONS = [
    "SDK 35", "SDK 34", "SDK 33", "SDK 32", "SDK 31", "SDK 30",
    "SDK 29", "SDK 28", "SDK 27", "iOS 15.4", "iOS 16.0", "iOS 17.0",
    "Windows 11", "Ubuntu 22.04", "Arch Linux", "Fedora 38"
]

APP_VERSIONS = [
    "Telegram Android 11.13.1", "Telegram Android 11.12.0", "Telegram Android 11.11.0",
    "Telegram Android 11.10.0", "Telegram Android 11.9.0", "Telegram Android 11.8.0",
    "Telegram Android 11.7.0", "Telegram Android 11.6.0", "Telegram Android 11.5.0",
    "Telegram iOS 10.4.1", "Telegram iOS 10.0.0", "Telegram iOS 11.0.0", "1.0"
]

def get_random_device() -> dict:
    return {
        "device_model": random.choice(DEVICE_MODELS),
        "system_version": random.choice(SYSTEM_VERSIONS),
        "app_version": random.choice(APP_VERSIONS),
        "lang_code": "ru",
        "system_lang_code": "ru-RU"
    }

_auth_sessions: dict[int, dict] = {}
_active_clients: dict[str, TelegramClient] = {}


def _make_client(name: str, api_id: int, api_hash: str) -> TelegramClient:
    Path("sessions").mkdir(exist_ok=True)
    device = get_random_device()
    return TelegramClient(
        f"sessions/{name}",
        api_id,
        api_hash,
        device_model=device["device_model"],
        system_version=device["system_version"],
        app_version=device["app_version"],
        lang_code=device["lang_code"],
        system_lang_code=device["system_lang_code"]
    )


async def auth_start(admin_id: int, name: str, api_id: int, api_hash: str, phone: str) -> tuple[bool, str]:
    try:
        client = _make_client(name, api_id, api_hash)
        await client.connect()

        if await client.is_user_authorized():
            await client.disconnect()
            return False, "Аккаунт уже авторизован"

        await client.send_code_request(phone)

        _auth_sessions[admin_id] = {
            "client": client,
            "phone": phone,
            "name": name,
            "api_id": api_id,
            "api_hash": api_hash
        }

        logger.info(f"Код запрошен для {phone}")
        return True, "Код отправлен"
    except Exception as e:
        logger.error(f"Ошибка auth_start: {e}")
        return False, str(e)


async def auth_verify_code(admin_id: int, code: str) -> tuple[bool | str, str]:
    if admin_id not in _auth_sessions:
        return False, "Сессия не найдена"

    session = _auth_sessions[admin_id]
    try:
        await session["client"].sign_in(session["phone"], code)
        await add_telethon_account(session["name"], session["api_id"], session["api_hash"], session["phone"])
        await session["client"].disconnect()
        del _auth_sessions[admin_id]
        logger.info(f"Авторизован: {session['name']}")
        return True, "Аккаунт добавлен"
    except SessionPasswordNeededError:
        return "2fa", "Введите пароль 2FA"
    except PhoneCodeInvalidError:
        return "retry", "Неверный код, попробуйте ещё раз"
    except Exception as e:
        logger.error(f"Ошибка кода: {e}")
        return False, str(e)


async def auth_verify_password(admin_id: int, password: str) -> tuple[bool, str]:
    if admin_id not in _auth_sessions:
        return False, "Сессия не найдена"

    session = _auth_sessions[admin_id]
    try:
        await session["client"].sign_in(password=password)
        await add_telethon_account(session["name"], session["api_id"], session["api_hash"], session["phone"])
        await session["client"].disconnect()
        del _auth_sessions[admin_id]
        logger.info(f"Авторизован (2FA): {session['name']}")
        return True, "Аккаунт добавлен"
    except Exception as e:
        logger.error(f"Ошибка пароля: {e}")
        return False, str(e)


async def auth_cancel(admin_id: int):
    if admin_id in _auth_sessions:
        sess = _auth_sessions[admin_id]
        if sess["client"].is_connected():
            await sess["client"].disconnect()
        del _auth_sessions[admin_id]


async def get_client(name: str, api_id: int, api_hash: str) -> TelegramClient:
    if name in _active_clients:
        client = _active_clients[name]
        if client.is_connected():
            return client
        del _active_clients[name]

    for attempt in range(3):
        try:
            client = _make_client(name, api_id, api_hash)
            await client.connect()
            if not await client.is_user_authorized():
                raise Exception("Клиент не авторизован")
            _active_clients[name] = client
            logger.info(f"Подключен клиент: {name}")
            return client
        except Exception as e:
            if "database is locked" in str(e):
                logger.warning(f"База заблокирована, попытка {attempt + 1}/3")
                await asyncio.sleep(1)
                continue
            logger.error(f"Ошибка подключения {name}: {e}")
            raise

    raise Exception("Не удалось подключиться: база данных заблокирована")


async def get_active_clients() -> list[TelegramClient]:
    accounts = await get_telethon_accounts()
    clients = []
    for acc in accounts:
        try:
            client = await get_client(acc['name'], acc['api_id'], acc['api_hash'])
            clients.append(client)
        except Exception as e:
            logger.warning(f"Не удалось подключить {acc['name']}: {e}")
    return clients


async def check_client_connection(client: TelegramClient) -> bool:
    try:
        return client.is_connected()
    except Exception:
        return False


async def disconnect_client(name: str):
    if name in _active_clients:
        try:
            await _active_clients[name].disconnect()
            del _active_clients[name]
        except Exception as e:
            logger.error(f"Ошибка отключения {name}: {e}")


async def disconnect_all():
    for client in _active_clients.values():
        if client.is_connected():
            await client.disconnect()
    _active_clients.clear()