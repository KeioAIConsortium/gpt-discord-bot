import os

from dotenv import load_dotenv

load_dotenv()


DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
DISCORD_CLIENT_ID = os.environ["DISCORD_CLIENT_ID"]

# Send Messages, Create Public Threads, Send Messages in Threads, Manage Messages, Manage Threads, Read Message History, Use Slash Command
BOT_INVITE_URL = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&permissions=328565073920&scope=bot"

DEFAULT_MODEL = os.environ["DEFAULT_MODEL"]
