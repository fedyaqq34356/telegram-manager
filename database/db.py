import aiosqlite
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from config import settings

DB_PATH = settings.DATABASE_URL

@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        yield db

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                language TEXT DEFAULT 'ru',
                created_at TEXT DEFAULT (datetime('now')),
                demo_activated INTEGER DEFAULT 0,
                demo_expires_at TEXT,
                custom_bot_token TEXT
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sub_type TEXT NOT NULL,
                plan TEXT NOT NULL,
                reactions_count INTEGER DEFAULT 5,
                views_count INTEGER DEFAULT 5,
                months INTEGER DEFAULT 1,
                max_channels INTEGER DEFAULT 1,
                started_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(tg_id)
            );

            CREATE TABLE IF NOT EXISTS user_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                channel_title TEXT,
                channel_username TEXT,
                custom_bot_token TEXT,
                use_custom_bot INTEGER DEFAULT 0,
                added_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(tg_id)
            );

            CREATE TABLE IF NOT EXISTS reaction_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                reactions TEXT DEFAULT '[]',
                interval_minutes INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 0,
                UNIQUE(user_id, channel_id),
                FOREIGN KEY (user_id) REFERENCES users(tg_id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount TEXT,
                currency TEXT,
                method TEXT,
                status TEXT DEFAULT 'pending',
                tx_hash TEXT,
                sub_type TEXT,
                plan TEXT,
                months INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(tg_id)
            );

            CREATE TABLE IF NOT EXISTS telethon_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                api_id INTEGER NOT NULL,
                api_hash TEXT NOT NULL,
                phone TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                added_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS crypto_wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                currency TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                text_content TEXT,
                media_type TEXT,
                media_file_id TEXT,
                buttons TEXT DEFAULT '[]',
                scheduled_at TEXT NOT NULL,
                sent INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS daily_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                usage_type TEXT NOT NULL,
                date TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                UNIQUE(user_id, usage_type, date)
            );

            CREATE TABLE IF NOT EXISTS subscription_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                reactions_count INTEGER,
                views_count INTEGER,
                price_1m REAL,
                price_3m REAL,
                price_6m REAL,
                price_12m REAL,
                is_active INTEGER DEFAULT 1
            );

            INSERT OR IGNORE INTO bot_settings (key, value) VALUES
                ('welcome_message', 'Добро пожаловать в бот! 👋'),
                ('demo_duration_hours', '24'),
                ('free_circles_per_day', '3'),
                ('free_posts_per_day', '3'),
                ('circles_sub_price', '100'),
                ('posts_sub_price', '100'),
                ('full_sub_price', '500'),
                ('stars_per_channel', '100');

            INSERT OR IGNORE INTO subscription_plans (name, reactions_count, views_count, price_1m, price_3m, price_6m, price_12m) VALUES
                ('Старт', 5, 5, 10, 25, 45, 80),
                ('Базовый', 10, 10, 15, 35, 65, 120),
                ('Продвинутый', 15, 15, 20, 50, 90, 160),
                ('Профи', 20, 20, 30, 75, 140, 250),
                ('Ультра', 50, 50, 60, 150, 280, 500);
        """)
        await db.commit()

    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_reaction_settings_user_channel "
                "ON reaction_settings(user_id, channel_id)"
            )
            await db.commit()
        except Exception:
            pass

    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("ALTER TABLE users ADD COLUMN custom_bot_token TEXT")
            await db.commit()
        except Exception:
            pass

async def get_user(tg_id: int) -> aiosqlite.Row | None:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        return await cursor.fetchone()

async def create_user(tg_id: int, username: str, full_name: str, language: str = 'ru'):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (tg_id, username, full_name, language) VALUES (?, ?, ?, ?)",
            (tg_id, username, full_name, language)
        )
        await db.commit()

async def update_user_language(tg_id: int, language: str):
    async with get_db() as db:
        await db.execute("UPDATE users SET language = ? WHERE tg_id = ?", (language, tg_id))
        await db.commit()

async def get_user_custom_token(tg_id: int) -> str | None:
    async with get_db() as db:
        cursor = await db.execute("SELECT custom_bot_token FROM users WHERE tg_id = ?", (tg_id,))
        row = await cursor.fetchone()
        return row['custom_bot_token'] if row else None

async def set_user_custom_token(tg_id: int, token: str):
    async with get_db() as db:
        await db.execute("UPDATE users SET custom_bot_token = ? WHERE tg_id = ?", (token, tg_id))
        await db.commit()

async def get_users_with_custom_bots() -> list:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT tg_id, custom_bot_token FROM users WHERE custom_bot_token IS NOT NULL AND custom_bot_token != ''"
        )
        return await cursor.fetchall()

async def activate_demo(tg_id: int, hours: int = 24):
    expires = (datetime.now() + timedelta(hours=hours)).isoformat()
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET demo_activated = 1, demo_expires_at = ? WHERE tg_id = ?",
            (expires, tg_id)
        )
        await db.commit()

async def get_active_subscription(tg_id: int) -> aiosqlite.Row | None:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? AND is_active = 1 AND expires_at > datetime('now') ORDER BY expires_at DESC LIMIT 1",
            (tg_id,)
        )
        return await cursor.fetchone()

async def create_subscription(user_id: int, sub_type: str, plan: str, reactions_count: int, views_count: int, months: int, max_channels: int = 1):
    expires = (datetime.now() + timedelta(days=30 * months)).isoformat()
    async with get_db() as db:
        await db.execute(
            "UPDATE subscriptions SET is_active = 0 WHERE user_id = ? AND sub_type = ?",
            (user_id, sub_type)
        )
        await db.execute(
            "INSERT INTO subscriptions (user_id, sub_type, plan, reactions_count, views_count, months, max_channels, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, sub_type, plan, reactions_count, views_count, months, max_channels, expires)
        )
        await db.commit()

async def add_user_channel(user_id: int, channel_id: int, channel_title: str, channel_username: str, custom_bot_token: str = None):
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO user_channels (user_id, channel_id, channel_title, channel_username, custom_bot_token, use_custom_bot) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, channel_id, channel_title, channel_username, custom_bot_token, 1 if custom_bot_token else 0)
        )
        await db.commit()

async def get_user_channels(user_id: int) -> list:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM user_channels WHERE user_id = ?", (user_id,))
        return await cursor.fetchall()

async def get_channel(user_id: int, channel_id: int) -> aiosqlite.Row | None:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM user_channels WHERE user_id = ? AND channel_id = ?",
            (user_id, channel_id)
        )
        return await cursor.fetchone()

async def remove_user_channel(user_id: int, channel_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM user_channels WHERE user_id = ? AND channel_id = ?", (user_id, channel_id))
        await db.commit()

async def get_reaction_settings(user_id: int, channel_id: int) -> aiosqlite.Row | None:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM reaction_settings WHERE user_id = ? AND channel_id = ?",
            (user_id, channel_id)
        )
        return await cursor.fetchone()

async def upsert_reaction_settings(user_id: int, channel_id: int, reactions: list, interval: int, is_active: bool):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO reaction_settings (user_id, channel_id, reactions, interval_minutes, is_active)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id, channel_id) DO UPDATE SET
               reactions = excluded.reactions, interval_minutes = excluded.interval_minutes, is_active = excluded.is_active""",
            (user_id, channel_id, json.dumps(reactions), interval, int(is_active))
        )
        await db.commit()

async def upsert_reaction_settings_field(user_id: int, channel_id: int, **kwargs):
    async with get_db() as db:
        existing = await (await db.execute(
            "SELECT * FROM reaction_settings WHERE user_id = ? AND channel_id = ?",
            (user_id, channel_id)
        )).fetchone()
        if not existing:
            await db.execute(
                "INSERT INTO reaction_settings (user_id, channel_id) VALUES (?, ?)",
                (user_id, channel_id)
            )
        for key, value in kwargs.items():
            if key == 'reactions':
                value = json.dumps(value)
            await db.execute(
                f"UPDATE reaction_settings SET {key} = ? WHERE user_id = ? AND channel_id = ?",
                (value, user_id, channel_id)
            )
        await db.commit()

async def get_all_active_reaction_settings() -> list:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT rs.*, uc.custom_bot_token FROM reaction_settings rs JOIN user_channels uc ON rs.user_id = uc.user_id AND rs.channel_id = uc.channel_id WHERE rs.is_active = 1"
        )
        return await cursor.fetchall()

async def get_telethon_accounts() -> list:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM telethon_accounts WHERE is_active = 1")
        return await cursor.fetchall()

async def add_telethon_account(name: str, api_id: int, api_hash: str, phone: str):
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO telethon_accounts (name, api_id, api_hash, phone) VALUES (?, ?, ?, ?)",
            (name, api_id, api_hash, phone)
        )
        await db.commit()

async def remove_telethon_account(name: str):
    async with get_db() as db:
        await db.execute("UPDATE telethon_accounts SET is_active = 0 WHERE name = ?", (name,))
        await db.commit()

async def get_crypto_wallets() -> list:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM crypto_wallets WHERE is_active = 1")
        return await cursor.fetchall()

async def add_crypto_wallet(currency: str, address: str):
    async with get_db() as db:
        await db.execute("INSERT INTO crypto_wallets (currency, wallet_address) VALUES (?, ?)", (currency, address))
        await db.commit()

async def remove_crypto_wallet(wallet_id: int):
    async with get_db() as db:
        await db.execute("UPDATE crypto_wallets SET is_active = 0 WHERE id = ?", (wallet_id,))
        await db.commit()

async def create_payment(user_id: int, amount: str, currency: str, method: str, sub_type: str, plan: str, months: int, channels_count: int = 1) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO payments (user_id, amount, currency, method, sub_type, plan, months) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, amount, currency, method, sub_type, plan, months)
        )
        await db.commit()
        return cursor.lastrowid

async def update_payment_status(payment_id: int, status: str, tx_hash: str = None):
    async with get_db() as db:
        await db.execute(
            "UPDATE payments SET status = ?, tx_hash = ? WHERE id = ?",
            (status, tx_hash, payment_id)
        )
        await db.commit()

async def get_payment(payment_id: int) -> aiosqlite.Row | None:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        return await cursor.fetchone()

async def get_setting(key: str, default: str = '') -> str:
    async with get_db() as db:
        cursor = await db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row['value'] if row else default

async def set_setting(key: str, value: str):
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()

async def get_daily_usage(user_id: int, usage_type: str) -> int:
    today = datetime.now().strftime('%Y-%m-%d')
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT count FROM daily_usage WHERE user_id = ? AND usage_type = ? AND date = ?",
            (user_id, usage_type, today)
        )
        row = await cursor.fetchone()
        return row['count'] if row else 0

async def increment_daily_usage(user_id: int, usage_type: str):
    today = datetime.now().strftime('%Y-%m-%d')
    async with get_db() as db:
        await db.execute(
            "INSERT INTO daily_usage (user_id, usage_type, date, count) VALUES (?, ?, ?, 1) ON CONFLICT(user_id, usage_type, date) DO UPDATE SET count = count + 1",
            (user_id, usage_type, today)
        )
        await db.commit()

async def get_all_users() -> list:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM users")
        return await cursor.fetchall()

async def get_stats() -> dict:
    async with get_db() as db:
        today = datetime.now().strftime('%Y-%m-%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        total = (await (await db.execute("SELECT COUNT(*) as c FROM users")).fetchone())['c']
        new_today = (await (await db.execute("SELECT COUNT(*) as c FROM users WHERE date(created_at) = ?", (today,))).fetchone())['c']
        new_week = (await (await db.execute("SELECT COUNT(*) as c FROM users WHERE date(created_at) >= ?", (week_ago,))).fetchone())['c']
        new_month = (await (await db.execute("SELECT COUNT(*) as c FROM users WHERE date(created_at) >= ?", (month_ago,))).fetchone())['c']
        demo_count = (await (await db.execute("SELECT COUNT(*) as c FROM users WHERE demo_activated = 1")).fetchone())['c']
        paid_count = (await (await db.execute("SELECT COUNT(DISTINCT user_id) as c FROM subscriptions WHERE is_active = 1")).fetchone())['c']
        crypto_pays = (await (await db.execute("SELECT COUNT(*) as c FROM payments WHERE method = 'crypto' AND status = 'approved'")).fetchone())['c']
        stars_pays = (await (await db.execute("SELECT COUNT(*) as c FROM payments WHERE method = 'stars' AND status = 'approved'")).fetchone())['c']
        
        ru_users = (await (await db.execute("SELECT COUNT(*) as c FROM users WHERE language = 'ru'")).fetchone())['c']
        en_users = (await (await db.execute("SELECT COUNT(*) as c FROM users WHERE language = 'en'")).fetchone())['c']

        return {
            'total': total, 'new_today': new_today, 'new_week': new_week, 'new_month': new_month,
            'demo_count': demo_count, 'paid_count': paid_count,
            'crypto_pays': crypto_pays, 'stars_pays': stars_pays,
            'ru_users': ru_users, 'en_users': en_users
        }

async def add_scheduled_post(user_id: int, channel_id: int, text: str, media_type: str, media_file_id: str, buttons: list, scheduled_at: datetime):
    async with get_db() as db:
        await db.execute(
            "INSERT INTO scheduled_posts (user_id, channel_id, text_content, media_type, media_file_id, buttons, scheduled_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, channel_id, text, media_type, media_file_id, json.dumps(buttons), scheduled_at.isoformat())
        )
        await db.commit()

async def get_pending_posts() -> list:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM scheduled_posts WHERE sent = 0 AND scheduled_at <= datetime('now')"
        )
        return await cursor.fetchall()

async def mark_post_sent(post_id: int):
    async with get_db() as db:
        await db.execute("UPDATE scheduled_posts SET sent = 1 WHERE id = ?", (post_id,))
        await db.commit()

async def get_subscription_plans() -> list:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM subscription_plans WHERE is_active = 1")
        return await cursor.fetchall()

async def get_pending_crypto_payments() -> list:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM payments WHERE method = 'crypto_manual' AND status = 'pending'"
        )
        return await cursor.fetchall()

async def get_users_with_subscription() -> list:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT DISTINCT u.* FROM users u JOIN subscriptions s ON u.tg_id = s.user_id WHERE s.is_active = 1 AND s.expires_at > datetime('now')"
        )
        return await cursor.fetchall()

async def get_users_without_demo() -> list:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM users WHERE demo_activated = 0")
        return await cursor.fetchall()

async def get_users_with_demo_no_sub() -> list:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT u.* FROM users u WHERE u.demo_activated = 1 AND u.tg_id NOT IN (SELECT user_id FROM subscriptions WHERE is_active = 1)"
        )
        return await cursor.fetchall()

async def get_user_payment_total(user_id: int) -> float:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT SUM(CAST(amount AS REAL)) as total FROM payments WHERE user_id = ? AND status = 'approved'",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row['total'] or 0.0

async def create_custom_plan_for_user(user_id: int, plan_name: str, reactions_count: int, views_count: int, price_usd: float, months: int):
    expires = (datetime.now() + timedelta(days=30 * months)).isoformat()
    async with get_db() as db:
        await db.execute(
            "UPDATE subscriptions SET is_active = 0 WHERE user_id = ? AND sub_type = 'custom'",
            (user_id,)
        )
        await db.execute(
            "INSERT INTO subscriptions (user_id, sub_type, plan, reactions_count, views_count, months, expires_at) VALUES (?, 'custom', ?, ?, ?, ?, ?)",
            (user_id, plan_name, reactions_count, views_count, months, expires)
        )
        await db.execute(
            "INSERT INTO payments (user_id, amount, currency, method, sub_type, plan, months, status) VALUES (?, ?, 'USD', 'admin_gift', 'custom', ?, ?, 'approved')",
            (user_id, str(price_usd), plan_name, months)
        )
        await db.commit()

async def get_source_channels_for_parser() -> list:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM user_channels")
        return await cursor.fetchall()

async def get_pending_crypto_invoices() -> list:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM payments WHERE method = 'crypto_auto' AND status = 'pending' AND tx_hash IS NOT NULL"
        )
        return await cursor.fetchall()