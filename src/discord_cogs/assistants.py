from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands
from src.constants import ACTIVATE_BUILD_THREAD_PREFIX
from src.discord_cogs._utils import should_block
from src.models.assistant import AssistantCreate
from src.openai_api.assistants import create_assistant, list_assistants

logger = logging.getLogger(__name__)


class Assistant(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="build")
    async def build(self, int: discord.Interaction, name: str):
        """Create an assistant"""
        try:
            # only support creating assistant in text channel
            if not isinstance(int.channel, discord.TextChannel):
                return

            # block servers not in allow list
            if should_block(guild=int.guild):
                return

            user = int.user
            logger.info(f"Build command by {user}")

            # Create embed
            embed = discord.Embed(
                description=f"<@{user.id}> wants to build an assistant! 🤖💬",
                color=discord.Color.blue(),
            )
            await int.response.send_message(embed=embed)

            # create the thread
            response = await int.original_response()
            thread = await response.create_thread(
                name=f"{ACTIVATE_BUILD_THREAD_PREFIX} - {name} - {user.name[:20]}",
                slowmode_delay=1,
                reason="gpt-bot",
                auto_archive_duration=60,
            )

            # Description
            await thread.send("What is the description of your assistant?")
            description = await self.bot.wait_for("message", check=lambda m: m.author == user)

            # Instructions
            await thread.send("What are the instructions for your assistant?")
            instructions = await self.bot.wait_for("message", check=lambda m: m.author == user)

            # TODO: add tools and file_ids
            created = await create_assistant(
                AssistantCreate(
                    name=name,
                    description=description.content,
                    instructions=instructions.content,
                )
            )

            return await thread.send(f"Created assistant `{created.id}`")

        except Exception as e:
            logger.exception(e)
            await int.response.send_message(f"Failed to start chat {str(e)}", ephemeral=True)

    @app_commands.command(name="list")
    async def list(self, int: discord.Interaction):
        """List all available assistants"""
        assistants = await list_assistants()
        rendered = ""
        for assistant in assistants:
            rendered += assistant.render()
        await int.response.send_message(rendered)


async def setup(bot):
    await bot.add_cog(Assistant(bot))
