import aiohttp
from config import settings

BASE_URL = settings.CRYPTO_PAY_URL
HEADERS = {"Crypto-Pay-API-Token": settings.CRYPTO_PAY_TOKEN}

async def create_invoice(asset: str, amount: float, description: str = "", payload: str = "") -> dict | None:
    async with aiohttp.ClientSession() as session:
        params = {
            "asset": asset,
            "amount": str(amount),
            "description": description,
            "payload": payload,
            "paid_btn_name": "openBot",
        }
        async with session.post(f"{BASE_URL}/createInvoice", headers=HEADERS, json=params) as resp:
            data = await resp.json()
            if data.get("ok"):
                return data["result"]
    return None

async def get_invoice(invoice_id: int) -> dict | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/getInvoices", headers=HEADERS, params={"invoice_ids": str(invoice_id)}) as resp:
            data = await resp.json()
            if data.get("ok") and data["result"]["items"]:
                return data["result"]["items"][0]
    return None

async def get_balance() -> list:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/getBalance", headers=HEADERS) as resp:
            data = await resp.json()
            if data.get("ok"):
                return data["result"]
    return []

async def get_exchange_rates() -> list:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/getExchangeRates", headers=HEADERS) as resp:
            data = await resp.json()
            if data.get("ok"):
                return data["result"]
    return []