"""
Edit this file to change the bot's content.
No coding knowledge needed — just change the text between the quotes.
"""

# ---------- Welcome message ----------
# Shown to users when they press /start.
# You can use HTML tags: <b>bold</b>, <i>italic</i>, <a href="URL">link</a>
WELCOME_TEXT = """<b>Welcome! 👋</b>

This is a placeholder for your main intro text.

<b>Featured items:</b>
• <b>Item One</b> — short description, e.g. "Up to 100% bonus"
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
# Buttons appear in the order listed here.
#
# The FIRST button is always the "main" one — by convention the channel link.
BUTTONS = [
    {"text": "📢 Join channel for more",   "url": "https://t.me/yourchannel"},
    {"text": "🎯 Item One",                "url": "https://example.com/one"},
    {"text": "🎯 Item Two",                "url": "https://example.com/two"},
    {"text": "🎯 Item Three",              "url": "https://example.com/three"},
    # Add more lines here whenever you want — example:
    # {"text": "🎯 Item Four",             "url": "https://example.com/four"},
]

# How many buttons per row in the keyboard. 1 = one per row (recommended).
BUTTONS_PER_ROW = 1

# ---------- Admin settings ----------
# Telegram user IDs allowed to use /broadcast.
# To find your ID: message @userinfobot on Telegram and it will tell you.
ADMIN_IDS = [
    123456789,   # replace with your real Telegram user ID
    # 987654321, # you can add a second admin like this
]

# ---------- Broadcast settings ----------
# Delay between sends during a broadcast, in seconds.
# Telegram limits bots to ~30 messages/sec, but keeping it slower is safer.
BROADCAST_DELAY_MIN = 0.05
BROADCAST_DELAY_MAX = 0.15
