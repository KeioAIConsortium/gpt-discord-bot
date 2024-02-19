from __future__ import annotations

import logging

import discord
import openai
from discord import app_commands
from discord.ext import commands

from src.constants import ACTIVATE_BUILD_THREAD_PREFIX
from src.discord_cogs._utils import should_block
from src.models.assistant import AssistantCreate
from src.models.assistant import Assistant as AssistantUpdate
from src.openai_api.assistants import (
    create_assistant,
    update_assistant,
    delete_assistant,
    get_assistant,
    list_assistants,
)

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

            return await thread.send(f"Created assistant `{created.id}` ")

        except Exception as e:
            logger.exception(e)
            await int.response.send_message(f"Failed to start chat {str(e)}", ephemeral=True)

    @app_commands.command(name="update")
    async def update(self, int: discord.Interaction, assistant_id: str):
        """Update an assistant"""
        try:
            # only support updating assistant in text channel
            if not isinstance(int.channel, discord.TextChannel):
                return

            # block servers not in allow list
            if should_block(guild=int.guild):
                return

            user = int.user
            logger.info(f"Update command by {user}")

            # Create embed
            embed = discord.Embed(
                description=f"<@{user.id}> wants to update an assistant! 🤖💬",
                color=discord.Color.blue(),
            )
            await int.response.send_message(embed=embed)

            # The current assistant
            assistant = await get_assistant(assistant_id)

            # create the thread
            response = await int.original_response()
            thread = await response.create_thread(
                name=f"{ACTIVATE_BUILD_THREAD_PREFIX} - {assistant.name} - {user.name[:20]}",
                slowmode_delay=1,
                reason="gpt-bot",
                auto_archive_duration=60,
            )

            # Description
            await thread.send("What is the new description of your assistant?")
            description = await self.bot.wait_for("message", check=lambda m: m.author == user)
            if description.content != '.':
                assistant.description = description.content

            # Instructions
            await thread.send("What are the new instructions for your assistant?")
            instructions = await self.bot.wait_for("message", check=lambda m: m.author == user)
            if instructions.content != '.':
                assistant.instructions = instructions.content

            # TODO: add tools and file_ids
            
            updated = await update_assistant(assistant)

            return await thread.send(f"Updated assistant `{updated.id}` ")

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

    @app_commands.command(name="delete")
    async def delete(self, int: discord.Interaction, assistant_id: str):
        """Delete the specified assistant"""
        await int.response.defer()  # defer the response to avoid timeout during openai_api call
        try:
            # only support deleting assistant in text channel
            if not isinstance(int.channel, discord.TextChannel):
                return

            # block servers not in allow list
            if should_block(guild=int.guild):
                return

            assistant = await get_assistant(assistant_id)

            embed = discord.Embed(
                title=f"Assistant {assistant.name}",
                description=f"Description: {assistant.description}",
                color=discord.Color.red(),
            )
            view = DeleteConfirmView(assistant=assistant)
            await int.followup.send(
                content=f"Are you sure you want to delete assistant `{assistant.id}`?",
                embed=embed,
                view=view,
            )

            user = int.user
            # TODO: check if the user has the permission to delete

            logger.info(f"Delete command by {user}")

        except Exception as e:
            if isinstance(e, openai.NotFoundError):
                if e.status_code == 404:
                    await int.followup.send(
                        f"Failed to delete assistant. No assistant found with id `{assistant_id}`."
                    )
            else:
                logger.exception(e)
                await int.followup.send(f"Failed to delete assistant. {str(e)}")


class DeleteConfirmView(discord.ui.View):
    def __init__(self, assistant: Assistant):
        super().__init__()
        self.assistant = assistant

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red)
    async def delete(self, int: discord.Interaction, button: discord.ui.Button):
        await delete_assistant(self.assistant.id)
        await int.response.send_message(
            f"Deleted assistant {self.assistant.name} by {int.user.mention}"
        )
        self.stop()
        # disable the buttons
        for item in self.children:
            item.disabled = True
        await int.followup.edit_message(message_id=int.message.id, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, int: discord.Interaction, button: discord.ui.Button):
        await int.response.send_message("Cancelled deleting assistant", ephemeral=True)
        self.stop()
        # delete the original message
        await int.followup.delete_message(int.message.id)


async def setup(bot):
    await bot.add_cog(Assistant(bot))
