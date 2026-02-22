import asyncio
import logging
from aiogram import Bot
from database.db import get_pending_crypto_invoices, update_payment_status, get_payment, create_subscription
from services.crypto_pay import check_invoice_paid

logger = logging.getLogger(__name__)


class CryptoPayPoller:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = True

    async def run(self):
        logger.info("CryptoPayPoller: запуск")
        while self.running:
            try:
                await self._check_invoices()
            except Exception as e:
                logger.error(f"CryptoPayPoller error: {e}")
            await asyncio.sleep(30)

    async def _check_invoices(self):
        from services.user_bot import get_bot_for_user
        payments = await get_pending_crypto_invoices()
        for payment in payments:
            invoice_id = payment["tx_hash"]
            if not invoice_id:
                continue
            try:
                paid = await check_invoice_paid(int(invoice_id))
                if paid:
                    logger.info(f"CryptoPayPoller: invoice {invoice_id} оплачен, активирую подписку для user {payment['user_id']}")
                    await update_payment_status(payment["id"], "approved")
                    await create_subscription(
                        payment["user_id"], "main", payment["plan"],
                        5, 5, payment["months"]
                    )
                    try:
                        send_bot = await get_bot_for_user(payment["user_id"]) or self.bot
                        await send_bot.send_message(
                            payment["user_id"],
                            "✅ <b>Оплата подтверждена!</b>\n\nПодписка активирована.",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"CryptoPayPoller: ошибка проверки invoice {invoice_id}: {e}")

    def stop(self):
        self.running = False