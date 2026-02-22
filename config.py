from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list[int] = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
    CRYPTO_PAY_TOKEN: str = os.getenv("CRYPTO_PAY_TOKEN", "")
    STARS_CHANNEL_ID: int = int(os.getenv("STARS_CHANNEL_ID", "0"))
    STARS_CHANNEL_INVITE: str = os.getenv("STARS_CHANNEL_INVITE", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "bot.db")
    CRYPTO_PAY_URL: str = "https://pay.crypt.bot/api"

settings = Settings()