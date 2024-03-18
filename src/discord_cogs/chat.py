from __future__ import annotations

from io import BytesIO

import logging

import discord
from discord import Message as DiscordMessage
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View

from src.constants import ACTIVATE_CHAT_THREAD_PREFIX, MAX_ASSISTANT_LIST
from src.discord_cogs._utils import (
    is_last_message_stale,
    should_block,
    split_into_shorter_messages,
)
from src.models.api_responce import ResponceData, ResponceStatus
from src.models.message import MessageCreate
from src.openai_api.assistants import list_assistants
from src.openai_api.thread_messages import create_thread, generate_response
from src.openai_api.files import upload_file

logger = logging.getLogger(__name__)


class Chat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="chat")
    async def chat(self, int: discord.Interaction, assistant_id : str = "Not selected",
            thread_id : str = None):
        """Start a chat with the bot in a thread"""
        try:
            # only support creating thread in text channel
            if not isinstance(int.channel, discord.TextChannel):
                return

            # block servers not in allow list
            if should_block(guild=int.guild):
                return

            user = int.user
            logger.info(f"Chat command by {user}")

            # Create embed
            embed = discord.Embed(
                description=f"<@{user.id}> wants to chat! 🤖💬",
                color=discord.Color.green(),
            )

            # Call openai api to create thread
            if thread_id is None:
                openai_thread = await create_thread()
                thread_id = openai_thread.id
            embed.add_field(name="thread_id", value=thread_id)
            embed.add_field(name="assistant_id", value=assistant_id)
            await int.response.send_message(embed=embed)

            # create the thread
            response = await int.original_response()
            thread = await response.create_thread(
                name=f"{ACTIVATE_CHAT_THREAD_PREFIX} {user.name[:20]}",
                slowmode_delay=1,
                reason="gpt-bot",
                auto_archive_duration=60,
            )

            if assistant_id != "Not selected":
                return

            # Show assistants as a select menu
            view = SelectView(thread=thread)
            assistants = await list_assistants(MAX_ASSISTANT_LIST)
            for assistant in assistants:
                view.selectMenu.add_option(
                    label=assistant.name,
                    value=assistant.id,
                    description=assistant.description,
                )
            await thread.send("Select your assistant", view=view)

        except Exception as e:
            logger.exception(e)
            await int.response.send_message(f"Failed to start chat {str(e)}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: DiscordMessage):
        try:
            # block servers not in allow list
            if should_block(guild=message.guild):
                return

            # ignore messages from the bot
            if message.author == self.bot.user:
                return

            # ignore messages not in a thread
            channel = message.channel
            if not isinstance(channel, discord.Thread):
                return

            # ignore threads not created by the bot
            thread = channel
            if thread.owner_id != self.bot.user.id:
                return

            # ignore threads that are archived locked or title is not what we want
            if (
                thread.archived
                or thread.locked
                or not thread.name.startswith(ACTIVATE_CHAT_THREAD_PREFIX)
            ):
                # ignore this thread
                return

            # TODO: add later
            # # wait a bit in case user has more messages
            # if SECONDS_DELAY_RECEIVING_MSG > 0:
            #     await asyncio.sleep(SECONDS_DELAY_RECEIVING_MSG)
            #     if is_last_message_stale(
            #         interaction_message=message,
            #         last_message=thread.last_message,
            #         bot_id=client.user.id,
            #     ):
            #         # there is another message, so ignore this one
            #         return

            logger.info(
                f"Thread message to process - {message.author}: {message.content[:50]} - {thread.name} {thread.jump_url}"
            )

            # Handle the message in the thread
            async with thread.typing():
                # get field of embed in the first message of thread
                openai_thread_id = thread.starter_message.embeds[0].fields[0].value
                openai_assistant_id = thread.starter_message.embeds[0].fields[1].value
                # TODO: appropriate error handling
                if openai_assistant_id == "Not selected":
                    await thread.send(
                        embed=discord.Embed(
                            description=f"**Invalid response** - assistant not selected",
                            color=discord.Color.yellow(),
                        )
                    )
                    return
                                
                # Add the files to the thread when message has attachments
                # TODO: Error handling when len(message.attachments) > 10 or size > 512MB
                # TODO: Restrict file types
                file_ids = []
                if message.attachments:
                    for attachment in message.attachments:
                        # Handle the attachment
                        pseudo_file = BytesIO(await attachment.read())
                        file_id = await upload_file(file=pseudo_file, purpose="assistants")
                        file_ids.append(file_id)

                # Generate the response
                response_data = await generate_response(
                    thread_id=openai_thread_id,
                    assistant_id=openai_assistant_id,
                    new_message=MessageCreate.from_discord_message(
                        thread_id=openai_thread_id,
                        author_name=message.author.display_name,
                        message=message.content,
                        file_ids=file_ids,
                    ),
                )

            if is_last_message_stale(
                interaction_message=message,
                last_message=thread.last_message,
                bot_id=self.bot.user.id,
            ):
                # there is another message and its not from us, so ignore this response
                return

            # send response
            await process_response(thread=thread, response_data=response_data)
        except Exception as e:
            logger.exception(e)


class SelectView(View):
    def __init__(self, *, thread: discord.Thread = None):
        super().__init__()
        self.thread = thread

    @discord.ui.select(cls=Select, placeholder="Not selected")
    async def selectMenu(self, int: discord.Interaction, select: Select):
        selected = select.values[0]
        for option in select.options:
            if option.value == selected:
                option.default = True
                break

        select.disabled = True
        await int.response.edit_message(view=self)

        # modify the starter embed in the thread
        embed = self.thread.starter_message.embeds[0]
        embed.set_field_at(-1, name="assistant_id", value=selected)
        await self.thread.starter_message.edit(embed=embed)


# TODO: remove unused args
async def process_response(thread: discord.Thread, response_data: ResponceData) -> None:
    status = response_data.status
    content = response_data.content
    status_text = response_data.status_text

    if status is ResponceStatus.OK:
        sent_message = None
        if not content:
            sent_message = await thread.send(
                embed=discord.Embed(
                    description=f"**Invalid response** - empty response",
                    color=discord.Color.yellow(),
                )
            )
        else:
            content_rendered = "".join([c.render() for c in content])
            shorter_response = split_into_shorter_messages(content_rendered)
            for r in shorter_response:
                sent_message = await thread.send(r)

    else:
        await thread.send(
            embed=discord.Embed(
                description=f"**Error** - {status_text}",
                color=discord.Color.yellow(),
            )
        )


async def setup(bot):
    await bot.add_cog(Chat(bot))
