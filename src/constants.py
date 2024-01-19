from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
DISCORD_CLIENT_ID = os.environ["DISCORD_CLIENT_ID"]

ALLOWED_SERVER_IDS: list[int] = []
server_ids = os.environ["ALLOWED_SERVER_IDS"].split(",")
for s in server_ids:
    ALLOWED_SERVER_IDS.append(int(s))

# Send Messages, Create Public Threads, Send Messages in Threads, Manage Messages, Manage Threads, Read Message History, Use Slash Command
BOT_INVITE_URL = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&permissions=328565073920&scope=bot"

DEFAULT_MODEL = os.environ["DEFAULT_MODEL"]

ACTIVATE_CHAT_THREAD_PREFIX = "💬✅"
INACTIVATE_CHAT_THREAD_PREFIX = "💬❌"
ACTIVATE_BUILD_THREAD_PREFIX = "🔨✅"
INACTIVATE_BUILD_THREAD_PREFIX = "🔨❌"
MAX_CHARS_PER_REPLY_MSG = 1500  # discord has a 2k limit, we just break message into 1.5k
