# Telegram Bot

A simple Telegram bot that:
- Greets users with a welcome message + photo + inline buttons on `/start`
- Lets admins broadcast messages to all users with `/broadcast`
- Is fully configured from one file (`config.py`)
- Deploys to Railway in a few clicks

## Project structure

```
promo-bot/
├── bot.py              # main bot logic — you usually don't edit this
├── config.py           # ← edit this to change content
├── images/
│   └── welcome.jpg     # drop your welcome photo here
├── .env                # bot token (gitignored)
├── .env.example
├── requirements.txt    # Python dependencies
├── Procfile            # tells Railway how to run the bot
├── .gitignore
└── README.md
```

## Step 1 — Create your bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Pick a display name (e.g. "My Promo Bot")
4. Pick a username — must end in `bot` (e.g. `mypromo_bot`)
5. BotFather sends you a **token** that looks like `123456789:AAAA...` — keep it secret

## Step 2 — Get your Telegram user ID (for admin)

Message **@userinfobot** on Telegram. It replies with your numeric user ID. Copy that.

## Step 3 — Configure

1. Copy `.env.example` to `.env`
2. Paste your bot token after `BOT_TOKEN=`
3. Open `config.py` and:
   - Edit `WELCOME_TEXT`
   - Edit the `BUTTONS` list — add/remove/reorder freely
   - Put your photo in `images/` and update `WELCOME_IMAGE`
   - Put your user ID in `ADMIN_IDS`

## Step 4 — Run locally (to test)

```bash
python -m venv venv
source venv/bin/activate          # Mac/Linux
# OR  venv\Scripts\activate       # Windows

pip install -r requirements.txt
python bot.py
```

Open Telegram, find your bot, press `/start`. You should see your welcome message with the photo and buttons.

## Step 5 — Deploy to Railway (always-on)

1. Make a free account at <https://railway.app>
2. Push this folder to a GitHub repo, OR use Railway's CLI to deploy directly
3. In Railway:
   - **New Project → Deploy from GitHub repo** (pick your repo)
   - Once deployed, go to **Variables** tab and add:
     - `BOT_TOKEN` = your bot token from BotFather
4. Railway auto-detects the `Procfile` and runs `python bot.py` as a worker
5. Done — your bot is now online 24/7

**Important about the database:** Railway's free tier uses ephemeral disk by default, meaning `users.db` may reset on redeploy. For persistence, add a Railway **Volume** mounted at `/app/` (or use a Railway Postgres plugin and adapt the code). For a small bot, ephemeral is usually fine for the first weeks.

## How to add a new button

Open `config.py` and add a line to the `BUTTONS` list:

```python
BUTTONS = [
    {"text": "📢 Join channel for more",   "url": "https://t.me/yourchannel"},
    {"text": "🎯 Item One",                "url": "https://example.com/one"},
    {"text": "🎯 Item Two",                "url": "https://example.com/two"},
    {"text": "🎯 Item Three",              "url": "https://example.com/three"},
    {"text": "🎯 Item Four",               "url": "https://example.com/four"},  # ← new
]
```

Save the file. If running on Railway, redeploy (push to GitHub) and the new button appears.

## How to broadcast a message

Once your bot is running, message it (you must be in `ADMIN_IDS`):

- **Text broadcast:**
  ```
  /broadcast Hey everyone! New bonus dropped today.
  ```
- **Photo broadcast:** send a photo to the bot, then reply to that photo with:
  ```
  /broadcast Caption goes here
  ```

The bot will:
- Send to every user who has ever `/start`ed it
- Show a live progress update every 25 users
- Automatically remove users who blocked the bot
- Show a final summary (sent / blocked / failed)

## Commands summary

| Command | Who can use it | What it does |
|---------|---------------|--------------|
| `/start` | Anyone | Shows welcome message + buttons |
| `/help` | Anyone | Shows command list |
| `/users` | Admins only | Shows total user count |
| `/broadcast <text>` | Admins only | Sends text to all users |
| `/broadcast` (reply to photo) | Admins only | Sends photo + caption to all users |

## Troubleshooting

| Issue | Fix |
|------|------|
| `BOT_TOKEN not set` | Check your `.env` file has `BOT_TOKEN=...` |
| Bot doesn't reply | Make sure you pressed `/start`, not just sent a message |
| Photo not showing | Check the filename in `config.py` matches the file in `images/` |
| `/broadcast` doesn't work for you | Your Telegram ID isn't in `ADMIN_IDS` in `config.py` |
| Buttons in wrong order | Reorder lines in `BUTTONS` list |
