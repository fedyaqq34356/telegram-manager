# Telegram Manager Bot

A professional Telegram bot for automated channel management — automatic reactions, scheduled posting, video circles, and post parsing. Built with **aiogram 3.x + Telethon**, async SQLite, and full integration with **Crypto Bot API** for automatic cryptocurrency payments and native **Telegram Stars** payments.

---

## Features

### Core Functionality

- **Automatic Reactions:** Telethon worker accounts monitor user channels and place reactions on every new post. Reactions are selected randomly from the user's custom pool with a configurable delay between them
- **Video Circles:** Convert any video file into a Telegram video note (circle format). Free users get 3 circles per day; subscribers get unlimited
- **Scheduled Posting:** Post photos, videos, and text with inline URL buttons to connected channels — immediately or at a scheduled time
- **Post Parser:** Pull posts from any public Telegram channel and re-publish them to your channel with a configurable delay (+24h, +48h, +72h, +1 week, or custom hours)
- **Multi-channel Support:** Connect multiple channels per user (each additional channel costs Stars, price set in admin panel)
- **Two Channel Methods:** Add the main bot as admin to your channel, or create your own bot via @BotFather and provide the token

### Payment System

- **Crypto (Automatic):** Payments via Crypto Bot API — USDT, TON, BTC, ETH, LTC, BNB, TRX. Invoice created automatically, subscription activates within 30 seconds of payment without any admin action
- **Telegram Stars:** Official Telegram invoice (XTR currency). Subscription activates instantly on payment confirmation

### Subscription Plans

| Plan | Reactions / Views |
|------|-------------------|
| Start | 5 |
| Basic | 10 |
| Advanced | 15 |
| Pro | 20 |
| Ultra | 50 |

Available periods: **1 / 3 / 6 / 12 months**

Separate subscriptions for video circles and posting are available and fully configurable in the admin panel.

### Advanced Features

- **Demo Access:** New users get 24 hours of free access (duration configurable in admin panel)
- **Custom Plans:** Admins can create individual subscription plans for specific users with any parameters
- **Reaction Pool:** Users choose which emojis to use; reactions are always placed in random order
- **Reaction Interval:** Users set the delay in minutes between reactions
- **Inline Buttons in Posts:** Add URL buttons to posted content in format `Button Name | https://url.com`
- **Language Support:** Russian and English, selected at first start, changeable anytime
- **4 Background Services:** Main bot, ReactionWorker, Scheduler, and CryptoPayPoller run concurrently

---

## Requirements

- Python 3.10+
- ffmpeg (required for video circle conversion)
- Telegram Bot Token
- Crypto Bot API token (from [@CryptoBot](https://t.me/CryptoBot))
- Telethon accounts (regular Telegram accounts used as reaction workers)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/fedyaqq34356/telegram-manager.git
cd telegram-manager
```

### 2. Create virtual environment

```bash
python3 -m venv venv
```

### 3. Activate virtual environment

**Linux / macOS:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Install ffmpeg

**Ubuntu / Debian:**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

> Without ffmpeg the video circles feature will not work. All other features function normally without it.

---

## Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_IDS=123456789,987654321
CRYPTO_PAY_TOKEN=your_crypto_bot_api_token
STARS_CHANNEL_ID=-1001234567890
STARS_CHANNEL_INVITE=https://t.me/+xxxxxxxxx
DATABASE_URL=bot.db
```

**Getting BOT_TOKEN:**
- Message [@BotFather](https://t.me/BotFather) on Telegram
- Send `/newbot` and follow the instructions
- Copy the token to your `.env`

**Getting ADMIN_IDS:**
- Message [@userinfobot](https://t.me/userinfobot) to get your Telegram ID
- Add multiple admin IDs separated by commas
- Example: `ADMIN_IDS=123456789,987654321`

**Getting CRYPTO_PAY_TOKEN:**
- Open [@CryptoBot](https://t.me/CryptoBot)
- Go to **Crypto Pay → Create App**
- Copy the token to your `.env`

**Getting STARS_CHANNEL_ID:**
- Create a Telegram channel for Stars payment verification
- Add your bot as administrator
- Forward any message from the channel to [@userinfobot](https://t.me/userinfobot) to get the ID (starts with `-100`)

**Getting STARS_CHANNEL_INVITE:**
- In your channel settings, create an invite link
- Format: `https://t.me/+xxxxxxxxx`

---

## Running the Bot

```bash
python main.py
```

On successful start, console output will show:

```
Start polling
Run polling for bot
ReactionWorker started
Scheduler started
CryptoPayPoller started
```

All logs are written automatically to:
- `logs/bot.log` — full debug log with rotation (10MB × 5 files)
- `logs/errors.log` — errors only (5MB × 3 files)
- Console — INFO level and above in real time

---

## Project Structure

```
telegram-manager/
├── main.py                    # Entry point, starts all 4 services
├── config.py                  # Settings, environment variable loading
├── logger.py                  # Centralized logging (console + files)
│
├── database/
│   └── db.py                  # All database operations (aiosqlite)
│
├── handlers/
│   ├── start.py               # /start, language selection, onboarding flow
│   ├── channel.py             # Channel connection (method 1 and method 2)
│   ├── reactions.py           # Reaction pool setup, interval settings
│   ├── subscription.py        # Subscription purchase and payment flow
│   ├── posting.py             # Post creation and scheduling
│   ├── circles.py             # Video to circle conversion
│   ├── parser.py              # Post parser from external channels
│   └── admin.py               # Admin panel handlers
│
├── keyboards/
│   ├── main_kb.py             # User-facing reply and inline keyboards
│   └── admin_kb.py            # Admin panel keyboards
│
├── services/
│   ├── telethon_manager.py    # Telethon account auth and session management
│   ├── reaction_worker.py     # Background service — places reactions
│   ├── scheduler.py           # Background service — publishes scheduled posts
│   └── crypto_poller.py       # Background service — polls crypto invoice status
│
├── locales.py                 # RU / EN translation strings
├── sessions/                  # Telethon .session files (auto-created)
├── logs/                      # Log files (auto-created)
├── requirements.txt
├── .env                       # Your credentials (never commit this)
└── .gitignore
```

---

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────┐
│                 User Interface                  │
│             (Telegram Messages)                 │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│               Handler Layer                     │
│  ┌──────┬─────────┬──────────┬────────┬───────┐ │
│  │ Start│ Channel │Reactions │ Posts  │ Admin │ │
│  └──────┴─────────┴──────────┴────────┴───────┘ │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│            Background Services                  │
│  ┌─────────────┬───────────┬──────────────────┐ │
│  │ReactionWorker│ Scheduler│ CryptoPayPoller  │ │
│  └─────────────┴───────────┴──────────────────┘ │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│                Data Layer                       │
│  ┌──────────────────┬───────────────────────┐   │
│  │ SQLite Database  │  Telethon MTProto      │   │
│  │ (aiosqlite)      │  (Reaction workers)    │   │
│  └──────────────────┴───────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### 4 Services Running at All Times

| Service | Role |
|---------|------|
| aiogram dispatcher | Handles all user messages, callbacks, and commands |
| ReactionWorker | Listens for new posts via Telethon, places reactions |
| Scheduler | Checks database every 30 seconds and publishes due posts |
| CryptoPayPoller | Checks pending crypto invoices every 30 seconds |

### Reaction Lifecycle

```
[Admin adds Telethon account] → [Account authorized via phone + code + 2FA]
                                          │
[User configures reaction pool + interval]
                                          │
[ReactionWorker registers event listener on channel]
                                          │
[New post appears in channel]
           │
[Wait user-configured interval (minutes)]
           │
[Randomly select up to 3 Telethon accounts]
           │
[Each account places a random reaction from pool]
           │
[Small random delay between each account's reaction]
```

### Crypto Payment Lifecycle

```
[User selects crypto asset] → [Bot creates invoice via Crypto Bot API]
                                          │
              [Bot sends user payment link to @CryptoBot]
                                          │
              [CryptoPayPoller checks status every 30 seconds]
                                          │
              [Invoice marked as paid by Crypto Bot API]
                                          │
              [Subscription activated automatically]
                                          │
              [User receives notification]
```

### Stars Payment Lifecycle

```
[User selects Stars payment] → [Bot sends official Telegram invoice (XTR)]
                                          │
              [User pays inside Telegram interface]
                                          │
              [successful_payment event fires]
                                          │
              [Subscription activated instantly]
```

### Scheduled Post Lifecycle

```
[User sends content + selects time] → [Saved to scheduled_posts table]
                                               │
              [Scheduler checks DB every 30 seconds]
              [WHERE sent=0 AND scheduled_at <= now()]
                                               │
              [Post published to target channel]
                                               │
              [Marked as sent in database]
```

### Post Parser Lifecycle

```
[User enters @source_channel] → [Telethon reads last N posts]
                                          │
              [User selects delay: +24h / +48h / +72h / +1 week / custom]
                                          │
              [Each post saved: scheduled_at = original_date + delay]
                                          │
              [Scheduler publishes posts automatically at correct time]
```

> **Note on link replacement in parsed posts:** Automatic replacement of links inside parsed posts was worked on extensively but could not be brought to a reliable result. Telethon stores inline links as internal `MessageEntityTextUrl` entities, and replacing URLs without breaking text formatting proved too fragile. This feature will be revisited in a future release.

---

## User Flow

### First Launch

```
User: /start
Bot:  Hello / Привет
      Please choose your language:
      [🇺🇸 English] [🇷🇺 Русский]

User: [🇺🇸 English]
Bot:  Hello again! You have demo access for 24 hours.

Bot:  To get started, connect your channel.
      You have two options:
      [1 — Add this bot as admin] [2 — Create your own bot]
```

### Channel Connection — Method 1 (Add Main Bot)

```
User: [1 — Add this bot as admin]
Bot:  Add @YourBot to your PRIVATE channel as administrator.

[User adds bot to channel]

Bot:  Bot added! Please make it administrator.

[User promotes bot]

Bot:  Great! Bot is now administrator.
      Now add these Telethon accounts as administrators with all permissions:
      • @account1
      • @account2
      When done, press Ready.
      [Ready]

User: [Ready]
Bot:  (checks each Telethon account's membership)
      All accounts verified! ✅
      — or —
      These accounts were not found in the channel:
      @account2
```

### Channel Connection — Method 2 (Own Bot Token)

```
User: [2 — Create your own bot]
Bot:  Create a bot via @BotFather and send us its token.

User: 1234567890:AAzQcZWQqQ...
Bot:  Token accepted! Now add your bot to your channel as administrator.
      When done, press Ready.
      [Ready]

User: [Ready]
Bot:  Great! Now add these Telethon accounts as administrators:
      • @account1
      • @account2
      [Ready]
```

### After Setup

```
User: /ready
Bot:  [Main keyboard appears]
      🚀 Launch  |  💎 Buy Subscription
      ⚙️ Settings
```

### Configuring Reactions

```
User: [🚀 Launch] → [Configure Reactions]
Bot:  Select reactions for your channel:
      [👍] [❤️] [🔥] [🎉] [😮] [😢] [👎]
      [😁] [🤩] [💯] [🏆] [✍️] [🎁] [🙏]

User: [👍] [❤️] [🔥]  ← selects 3 emojis
User: [Done]
Bot:  Set delay between reactions (in minutes):

User: 2
Bot:  Reactions configured!
      Pool: 👍 ❤️ 🔥
      Delay: 2 minutes
```

### Buying a Subscription

```
User: [💎 Buy Subscription]
Bot:  Choose a plan:
      [Start — 5 reactions]
      [Basic — 10 reactions]
      [Advanced — 15 reactions]
      [Pro — 20 reactions]
      [Ultra — 50 reactions]

User: [Pro — 20 reactions]
Bot:  Choose period:
      [1 month — $X] [3 months — $X]
      [6 months — $X] [12 months — $X]

User: [3 months — $X]
Bot:  Choose payment method:
      [💎 Crypto] [⭐ Stars]
```

**Crypto payment:**
```
User: [💎 Crypto]
Bot:  Choose cryptocurrency:
      [USDT] [TON] [BTC] [ETH]
      [LTC]  [BNB] [TRX]

User: [USDT]
Bot:  Invoice created!
      [Pay via CryptoBot]  [✅ Check payment]

[User pays in @CryptoBot]
[Within 30 seconds — automatic detection]

Bot:  ✅ Payment confirmed! Subscription Pro — 3 months is now active.
```

**Stars payment:**
```
User: [⭐ Stars]
Bot:  How many channels?
      [1 channel — 100 ⭐] [3 channels — 300 ⭐]

[Telegram invoice appears]
[User pays]

Bot:  ✅ Subscription activated!
```

### Video Circles

```
User: [⚙️ Settings] → [🎥 Video Circles]
Bot:  Send me a video and I will convert it to a circle.
      Free: 3 per day | With subscription: unlimited

User: [sends video file]
Bot:  [sends back video note — circle format]
      Post to your channel?
      [📢 Post to channel] [Skip]
```

### Scheduled Posting

```
User: [⚙️ Settings] → [📢 Post to Channel]
Bot:  Choose channel:
      [My Channel 1] [My Channel 2]

User: [My Channel 1]
Bot:  Send your content (text / photo / video).
      To add buttons, add lines in format:
      Button Name | https://url.com

User: [sends photo with caption]
Bot:  When to send?
      [Send now] [Schedule]

User: [Schedule]
Bot:  Enter date and time (DD.MM.YYYY HH:MM):

User: 25.03.2026 18:00
Bot:  ✅ Post scheduled for 25.03.2026 18:00
```

### Post Parser

```
User: [⚙️ Settings] → [📋 Post Parser]
Bot:  Enter the @username of the source channel:

User: @some_news_channel
Bot:  How many posts to copy? (1–100):

User: 20
Bot:  Choose delay:
      [+24 hours] [+48 hours] [+72 hours]
      [+1 week]   [Custom]

User: [+24 hours]
Bot:  Select target channel:
      [My Channel 1]

User: [My Channel 1]
Bot:  ✅ 20 posts scheduled!
      They will be published 24 hours after their original dates.
```

---

## Admin Panel

Access by writing `/admin` or `/start` as an admin user.

### Statistics

```
Admin: [📊 Statistics]
Bot:
📊 Statistics

👥 Total users: 1,234
🆕 New today: 47
📅 This week: 312
🗓 This month: 891

🌍 By language:
  🇷🇺 RU: 987
  🇺🇸 EN: 247

🎯 Demo activated: 654
💎 Paid subscriptions: 213

💳 Crypto payments: 89
⭐ Stars payments: 124
```

### Broadcast

```
Admin: [📨 Broadcast]
Bot:   Choose audience:
       [👥 All users]        [✅ Has subscription]
       [🆕 Tried demo]       [🔴 No demo yet]
       [🇷🇺 Russian users]   [🇺🇸 English users]

Admin: [👥 All users]
Bot:   Send your message.
       To add a button, add a line:
       Button Name | https://url.com

Admin: Big sale! -30% on all plans this weekend!
       Learn more | https://t.me/yourchannel

Bot:   Broadcast complete!
       Sent: 1,228
       Errors: 6
```

### Export Users

```
Admin: [📤 Export Users]
Bot:   [sends users.txt]
```

File format — one line per user:
```
123456789   @johndoe    John Doe    +   $12.50
987654321   @janedoe    Jane Doe    -   $0.00
```

### Grant Subscription

```
Admin: [🎁 Grant Subscription]
Bot:   Enter Telegram ID of user:

Admin: 123456789
Bot:   User: John Doe (@johndoe)
       Choose plan:
       [Start] [Basic] [Advanced] [Pro] [Ultra]

Admin: [Pro]
Bot:   Choose period:
       [1 month] [3 months] [6 months] [12 months]

Admin: [3 months]
Bot:   ✅ Subscription Pro — 3 months granted to user 123456789

[User receives notification]
```

### Custom Subscription

```
Admin: [👤 Custom Subscription]
Bot:   Enter Telegram ID:

Admin: 123456789
Bot:   User: John Doe — Enter plan name:

Admin: VIP Partner
Bot:   Reactions per day:

Admin: 35
Bot:   Views per day:

Admin: 35
Bot:   Price in $ (0 if free):

Admin: 0
Bot:   Duration in months:

Admin: 6
Bot:   ✅ Custom subscription issued!
       John Doe — VIP Partner — 35 reactions — 6 months
```

### Adding Telethon Accounts

```
Admin: [🤖 Telethon Accounts] → [➕ Add account]
Bot:   Enter session name (example: acc1):

Admin: acc1
Bot:   Enter API ID (from my.telegram.org):

Admin: 12345678
Bot:   Enter API Hash:

Admin: abc123def456...
Bot:   Enter phone number (+79991234567):

Admin: +79991234567
Bot:   ✅ Code sent!
       Enter the code (spaces allowed: 1 2 3 4 5):

Admin: 1 2 3 4 5
Bot:   ✅ Account acc1 authorized and ready!
```

> **How to get API ID and API Hash:** Go to [my.telegram.org](https://my.telegram.org), log in with the Telethon account's phone number, go to **API development tools → Create application**, fill in any app name and platform, save the API ID and API Hash.

### Bot Settings

```
Admin: [⚙️ Bot Settings]
Bot:
welcome_message = Welcome! Demo access is active for 24 hours.
demo_duration_hours = 24
free_circles_per_day = 3
free_posts_per_day = 3
circles_sub_price = 100
posts_sub_price = 100
full_sub_price = 500
stars_per_channel = 100

Send: key value to change any setting.

Admin: demo_duration_hours 48
Bot:   ✅ Setting demo_duration_hours = 48 saved!
```

### Available Setting Keys

| Key | Description |
|-----|-------------|
| `welcome_message` | Welcome text shown to new users |
| `demo_duration_hours` | Free demo access duration in hours |
| `free_circles_per_day` | Free video circles per day |
| `free_posts_per_day` | Free posts per day |
| `circles_sub_price` | Stars price for circles subscription |
| `posts_sub_price` | Stars price for posting subscription |
| `full_sub_price` | Stars price for full subscription |
| `stars_per_channel` | Stars cost per additional channel |

---

## Troubleshooting

### Bot is not detecting new channel posts

- Verify bot (or Telethon account) is an administrator with "Read messages" permission
- Check that ReactionWorker started correctly in console output
- Make sure at least one Telethon account is added and active in admin panel

### Reactions are not being placed

- Verify Telethon accounts are added to the channel as administrators
- User must press "Start Bot" after configuring reactions
- Check `logs/errors.log` for Telethon connection errors
- Try removing and re-adding the Telethon account

### Crypto payment not activating

- Verify `CRYPTO_PAY_TOKEN` is correct in `.env`
- Check that CryptoPayPoller started in console output
- Payment activates within 30 seconds after Crypto Bot confirms it
- Check `logs/errors.log` for API errors

### Stars payment not activating

- Verify `STARS_CHANNEL_ID` and `STARS_CHANNEL_INVITE` are correct
- Bot must be administrator in the Stars channel
- The `successful_payment` event must be reaching the bot

### Video circles not working

- Ensure ffmpeg is installed: `ffmpeg -version`
- Install it: `sudo apt install ffmpeg`
- Check `logs/errors.log` for ffmpeg conversion errors

### Session file errors

- If a Telethon account session is corrupt, remove it in admin panel → it will be deleted from `sessions/`
- Never delete `.session` files manually while the bot is running

### Database locked

- Only one instance of the bot should be running at a time
- Stop all running instances before restarting
- Check with `ps aux | grep python`

### Bot not responding after restart

- Check that all environment variables in `.env` are correct
- Run `python main.py` directly in terminal to see startup errors
- Check `logs/errors.log` for startup exceptions

---

## Logging

Three log destinations are configured in `logger.py`:

| Destination | Level | Max size |
|-------------|-------|----------|
| Console (stdout) | INFO | — |
| `logs/bot.log` | DEBUG | 10MB × 5 files |
| `logs/errors.log` | ERROR | 5MB × 3 files |

Import the logger in any module:
```python
from logger import get_logger
logger = get_logger("reactions")

logger.info("New post in channel %s", channel_id)
logger.error("Failed to place reaction: %s", e)
```

---

## Deployment (VPS — Recommended)

```bash
# 1. Connect to your server
ssh user@your-server-ip

# 2. Clone and setup
git clone https://github.com/fedyaqq34356/telegram-manager.git
cd telegram-manager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo apt install ffmpeg

# 3. Configure credentials
nano .env

# 4. Test run
python main.py

# 5. Create systemd service
sudo nano /etc/systemd/system/tgmanager.service
```

Paste this content:

```ini
[Unit]
Description=Telegram Manager Bot
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/home/yourusername/telegram-manager
Environment=PATH=/home/yourusername/telegram-manager/venv/bin
ExecStart=/home/yourusername/telegram-manager/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable tgmanager
sudo systemctl start tgmanager
sudo systemctl status tgmanager

# View live logs
journalctl -u tgmanager -f

# Or directly from log file
tail -f logs/bot.log
```

### Docker (Alternative)

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

```bash
docker build -t tgmanager .
docker run -d --name tgmanager --env-file .env tgmanager
```

---

## Dependencies

```
aiogram==3.x          # Modern async Telegram Bot framework
telethon              # MTProto client for Telethon worker accounts
aiosqlite             # Async SQLite database
python-dotenv         # .env file support
aiohttp               # Async HTTP client for Crypto Bot API
```

Check for updates:
```bash
pip list --outdated
pip install --upgrade aiogram telethon
```

---

## Security

- Never commit `.env`, `sessions/`, or `logs/` to Git — already in `.gitignore`
- Admin IDs are verified on every single admin command — no privilege escalation possible
- Crypto Bot API token is only used server-side, never exposed to users
- Telethon `.session` files are equivalent to full account access — treat them like passwords and never share them
- Payment screenshots (if using manual flow) are sent only to admin chat

---

## Performance

| Metric | Value |
|--------|-------|
| Database | SQLite (suitable for up to ~100K users) |
| Memory usage | ~50–100MB typical |
| Reaction delay | Configurable per user (minutes) |
| Post scheduling precision | ±30 seconds |
| Crypto invoice detection | ±30 seconds after payment |
| Broadcast speed | ~30 messages/second |

For large user bases (50K+), consider migrating to PostgreSQL by replacing `aiosqlite` with `asyncpg`.

---

## Issues & Support

- **Bug reports and feature requests:** [github.com/fedyaqq34356/telegram-manager/issues](https://github.com/fedyaqq34356/telegram-manager/issues)
- **Repository:** [github.com/fedyaqq34356/telegram-manager](https://github.com/fedyaqq34356/telegram-manager)

---

## License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.

See `LICENSE` file for full text.

What this means:
- Free to use commercially
- Can modify and distribute
- Must disclose source code
- Must use the same license
- Must state changes made

---

Made with ❤️ for the Telegram community

Star this repo if you find it useful! ⭐