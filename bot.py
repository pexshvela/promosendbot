"""
Telegram Bot with Supabase
--------------------------
- /start: greets user, shows welcome text + photo + inline buttons,
          stores/updates user info in Supabase
- /broadcast: admin-only, sends a message to every active user
- /users: admin-only, shows total user count
- /stats: admin-only, shows detailed statistics
- /help: shows available commands

Run locally:  python bot.py
On Railway:   automatic via Procfile
"""

import asyncio
import logging
import os
import random
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
import db

# ---------- Setup ----------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise SystemExit("ERROR: BOT_TOKEN not set. Add it to .env (local) or Railway variables.")

if not config.ADMIN_IDS:
    print("WARNING: No ADMIN_IDS set. /broadcast, /users, /stats will be unusable.")
    print("Set ADMIN_IDS=123456789 in .env (local) or Railway variables.")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


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

    # Store/update the user in Supabase
    try:
        db.upsert_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code,
            is_premium=bool(user.is_premium),
        )
        log.info("User %s (%s) started — stored in Supabase", user.id, user.username)
    except Exception as e:
        log.error("Supabase upsert failed for user %s: %s", user.id, e)
        # Don't block the user experience if DB fails

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
            "/stats — detailed statistics",
            "/broadcast &lt;message&gt; — send a message to every user",
            "  ↳ Reply to a photo with /broadcast caption to broadcast a photo",
        ]
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def users_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        ids = db.get_all_active_user_ids()
        await update.message.reply_text(
            f"📊 Active users: <b>{len(ids)}</b>", parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"Error reading from Supabase: {e}")


async def stats_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        s = db.get_stats()
    except Exception as e:
        await update.message.reply_text(f"Error reading stats: {e}")
        return

    lines = [
        "📊 <b>Bot Stats</b>",
        "",
        f"👥 Total users: <b>{s['total']}</b>",
        f"   ├ Active: {s['active']}",
        f"   └ Blocked bot: {s['blocked']}",
        "",
        "📈 New users:",
        f"   ├ Today: {s['new_today']}",
        f"   ├ This week: {s['new_week']}",
        f"   └ This month: {s['new_month']}",
        "",
        f"⭐ Premium users: {s['premium']} ({s['premium_pct']}%)",
    ]

    if s["top_langs"]:
        lines.append("")
        lines.append("🌍 Top languages:")
        for i, (code, count) in enumerate(s["top_langs"], start=1):
            lines.append(f"   {i}. {code} — {count}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def broadcast_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin-only. Sends text (or photo+caption if replying to a photo) to all users."""
    if not is_admin(update.effective_user.id):
        return

    # Check if replying to a photo
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

    try:
        user_ids = db.get_all_active_user_ids()
    except Exception as e:
        await update.message.reply_text(f"Error reading user list: {e}")
        return

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
            # User blocked the bot — flag them
            try:
                db.mark_user_blocked(uid)
            except Exception:
                pass
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
    # For any non-command message, re-show the welcome
    await start(update, ctx)


# ---------- Main ----------
def main():
    # Verify Supabase tables exist (raises if not)
    db.ensure_schema()
    log.info("Supabase: schema verified")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, unknown))

    log.info("Bot starting…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
