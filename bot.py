"""
Telegram Bot
------------
- /start: greets user, shows welcome text + photo + inline buttons
- /broadcast: admin-only, sends a message to everyone who ever used /start
- /users: admin-only, shows total user count
- /help: shows available commands

Run locally:  python bot.py
On Railway:   automatic via Procfile
"""

import asyncio
import logging
import os
import random
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import Forbidden, BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config

# ---------- Setup ----------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise SystemExit("ERROR: BOT_TOKEN not set. Add it to .env (local) or Railway variables.")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "users.db"


# ---------- Database (stores users so admin can broadcast) ----------
def db_init():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id   INTEGER PRIMARY KEY,
                username  TEXT,
                first_name TEXT,
                joined_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def db_add_user(user_id: int, username: str | None, first_name: str | None):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username or "", first_name or ""),
        )


def db_remove_user(user_id: int):
    """Called when a user blocks the bot — keeps the DB clean."""
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM users WHERE user_id = ?", (user_id,))


def db_all_user_ids() -> list[int]:
    with sqlite3.connect(DB_PATH) as con:
        return [r[0] for r in con.execute("SELECT user_id FROM users")]


def db_user_count() -> int:
    with sqlite3.connect(DB_PATH) as con:
        return con.execute("SELECT COUNT(*) FROM users").fetchone()[0]


# ---------- Helpers ----------
def build_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard from config.BUTTONS, respecting BUTTONS_PER_ROW."""
    flat = [InlineKeyboardButton(b["text"], url=b["url"]) for b in config.BUTTONS]
    per_row = max(1, config.BUTTONS_PER_ROW)
    rows = [flat[i:i + per_row] for i in range(0, len(flat), per_row)]
    return InlineKeyboardMarkup(rows)


def build_welcome_text() -> str:
    text = config.WELCOME_TEXT.strip()
    if config.FOOTER_TEXT and config.FOOTER_TEXT.strip():
        text += "\n\n" + config.FOOTER_TEXT.strip()
    return text


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


# ---------- Handlers ----------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_add_user(user.id, user.username, user.first_name)
    log.info("User %s (%s) started the bot", user.id, user.username)

    text = build_welcome_text()
    keyboard = build_keyboard()

    image_path = BASE_DIR / config.WELCOME_IMAGE if config.WELCOME_IMAGE else None

    if image_path and image_path.exists():
        with open(image_path, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


async def help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lines = [
        "<b>Available commands:</b>",
        "/start — show the welcome message and buttons",
        "/help — this help text",
    ]
    if is_admin(user_id):
        lines += [
            "",
            "<b>Admin commands:</b>",
            "/users — show how many users are registered",
            "/broadcast &lt;message&gt; — send a message to every user",
            "  ↳ Reply to a photo with /broadcast caption to broadcast a photo",
        ]
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def users_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    count = db_user_count()
    await update.message.reply_text(f"📊 Total users: <b>{count}</b>", parse_mode=ParseMode.HTML)


async def broadcast_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin-only. Sends text (or photo+caption if replying to a photo) to all users."""
    if not is_admin(update.effective_user.id):
        return

    # If replying to a photo, broadcast that photo with the command's args as caption
    photo_file_id = None
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        photo_file_id = update.message.reply_to_message.photo[-1].file_id
        text = " ".join(ctx.args) if ctx.args else (update.message.reply_to_message.caption or "")
    else:
        text = " ".join(ctx.args)
        if not text:
            await update.message.reply_text(
                "Usage:\n"
                "<code>/broadcast your message here</code>\n\n"
                "Or reply to a photo with <code>/broadcast caption text</code> "
                "to broadcast that photo.",
                parse_mode=ParseMode.HTML,
            )
            return

    user_ids = db_all_user_ids()
    total = len(user_ids)
    status = await update.message.reply_text(f"📣 Broadcasting to {total} users…")

    sent = blocked = failed = 0
    for i, uid in enumerate(user_ids, start=1):
        try:
            if photo_file_id:
                await ctx.bot.send_photo(
                    chat_id=uid, photo=photo_file_id,
                    caption=text, parse_mode=ParseMode.HTML,
                )
            else:
                await ctx.bot.send_message(
                    chat_id=uid, text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            sent += 1
        except Forbidden:
            # User blocked the bot — remove them so we don't try again
            db_remove_user(uid)
            blocked += 1
        except BadRequest as e:
            failed += 1
            log.warning("BadRequest for %s: %s", uid, e)
        except Exception as e:
            failed += 1
            log.warning("Failed for %s: %s", uid, e)

        # Live progress update every 25 users
        if i % 25 == 0:
            try:
                await status.edit_text(
                    f"📣 Broadcasting… {i}/{total}\n"
                    f"✅ sent: {sent}  🚫 blocked: {blocked}  ⚠️ failed: {failed}"
                )
            except Exception:
                pass

        await asyncio.sleep(
            random.uniform(config.BROADCAST_DELAY_MIN, config.BROADCAST_DELAY_MAX)
        )

    await status.edit_text(
        f"✅ <b>Broadcast complete</b>\n\n"
        f"Total: {total}\n"
        f"Sent: {sent}\n"
        f"Blocked: {blocked}\n"
        f"Failed: {failed}",
        parse_mode=ParseMode.HTML,
    )


async def unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # For any non-command message, just re-show the welcome
    await start(update, ctx)


# ---------- Main ----------
def main():
    db_init()
    log.info("Database ready at %s", DB_PATH)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, unknown))

    log.info("Bot starting…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
