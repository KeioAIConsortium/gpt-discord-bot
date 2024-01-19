import discord
from discord import app_commands
from discord.ext import commands
from src.openai_api.assistants import list_assistants


class Assistant(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="list")
    async def list(self, int: discord.Interaction):
        """List all available assistants"""
        assistants = await list_assistants()
        rendered = ""
        for assistant in assistants:
            rendered += assistant.render() + "\n"
        await int.response.send_message(rendered)


async def setup(bot):
    await bot.add_cog(Assistant(bot))
