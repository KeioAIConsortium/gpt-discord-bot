import logging
from pathlib import Path

import discord
from discord.ext import commands

from src.constants import BOT_INVITE_URL, DISCORD_BOT_TOKEN

logging.basicConfig(
    format="[%(asctime)s] [%(filename)s:%(lineno)d] %(message)s", level=logging.INFO
)


class GPTBot(commands.Bot):
    def __init__(self, intents: discord.Intents) -> None:
        super().__init__(command_prefix="/", intents=intents, help_command=None)

    async def setup_hook(self):
        # Enable cogs in discord_cogs directory (except for files starting with _)
        cog_dir = Path(__file__).parent / "discord_cogs"
        for cog_path in cog_dir.glob("*.py"):
            cog_name = cog_path.stem
            if cog_name.startswith("_"):
                continue
            await bot.load_extension(f"src.discord_cogs.{cog_name}")

        await bot.tree.sync()

    async def on_ready(self):
        logging.info(f"We have logged in as {self.user}. Invite URL: {BOT_INVITE_URL}")


if __name__ == "__main__":
    # Define intents
    intents = discord.Intents.default()
    intents.message_content = True

    # Create bot instance and run
    bot = GPTBot(intents=intents)
    bot.run(DISCORD_BOT_TOKEN)
