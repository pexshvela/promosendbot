"""
Edit this file to change the bot's content.

For sensitive/environment-specific values (admin IDs, bot token, Supabase keys),
the bot reads from environment variables — set those in Railway's Variables tab.
"""

import os

# ---------- Welcome message ----------
# Shown to users when they press /start.
# You can use HTML tags: <b>bold</b>, <i>italic</i>, <a href="URL">link</a>
WELCOME_TEXT = """<b>Welcome! 👋</b>

You've just landed in the right place. We bring you the biggest welcome bonuses, exclusive offers, and trusted bookies — all in one spot. No fluff, no chasing, just the good deals.
📢 For daily offers & VIP drops, join our channel 👇

<b>Featured items:</b>
• <b>MadCasino</b> — 777% Welcome Bonus up to £7,500"
• <b>Item Two</b> — short description here
• <b>Item Three</b> — short description here
• <b>Item Four</b> — short description here

Tap a button below to learn more 👇
"""

# Footer text shown at the very end of the welcome message.
# Leave as empty string "" if you don't want one.
FOOTER_TEXT = ""

# ---------- Welcome image ----------
# Put your image file in the images/ folder and write the filename here.
# Set to None (without quotes) if you want text-only.
WELCOME_IMAGE = "images/welcome.jpg"

# ---------- Inline buttons ----------
# To add a new button, copy a line and change the text + URL.
# To remove one, delete or comment out (#) its line.
BUTTONS = [
    {"text": "📢 Join channel for more",   "url": "https://t.me/yourchannel"},
    {"text": "🎯 MadCasino",                "url": "https://example.com/one"},
    {"text": "🎯 Item Two",                "url": "https://example.com/two"},
    {"text": "🎯 Item Three",              "url": "https://example.com/three"},
    # Add more lines here whenever you want — example:
    # {"text": "🎯 Item Four",             "url": "https://example.com/four"},
]

# How many buttons per row in the keyboard. 1 = one per row (recommended).
BUTTONS_PER_ROW = 1

# ---------- Admin IDs (from environment variable) ----------
# In Railway: set a variable named ADMIN_IDS with comma-separated IDs:
#   ADMIN_IDS=123456789,987654321
# Find your ID by messaging @userinfobot on Telegram.
def _parse_admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_IDS", "").strip()
    if not raw:
        return []
    return [int(p.strip()) for p in raw.split(",") if p.strip().isdigit()]

ADMIN_IDS = _parse_admin_ids()

# ---------- Broadcast settings ----------
BROADCAST_DELAY_MIN = float(os.getenv("BROADCAST_DELAY_MIN", "0.05"))
BROADCAST_DELAY_MAX = float(os.getenv("BROADCAST_DELAY_MAX", "0.15"))

# ---------- Supabase ----------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # use the service_role key
