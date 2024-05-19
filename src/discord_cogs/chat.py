from __future__ import annotations

import os

import logging
import asyncio

import discord
from discord import Message as DiscordMessage
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View

from src.constants import ACTIVATE_CHAT_THREAD_PREFIX, MAX_ASSISTANT_LIST
from src.discord_cogs._utils import (
    is_last_message_stale,
    search_assistants,
    should_block,
    split_into_shorter_messages,
)
from src.models.api_response import ResponseData, ResponseStatus
from src.models.message import MessageCreate
from src.openai_api.assistants import list_assistants, get_assistant
from src.openai_api.thread_messages import create_thread, generate_response
from src.openai_api.files import upload_file

logger = logging.getLogger(__name__)

FILE_SEARCH_EXTENSION = [
    ".c", ".cs", ".cpp", ".doc", ".docx", ".html", ".java", ".json", 
    ".md", ".pdf", ".php", ".pptx", ".py", ".rb", ".tex", ".txt", 
    ".css", ".js", ".sh", ".ts"
]
CODE_INTERPRETER_EXTENSION = [
    ".c", ".cs", ".cpp", ".doc", ".docx", ".html", ".java", ".json", 
    ".md", ".pdf", ".php", ".pptx", ".py", ".rb", ".tex", ".txt", 
    ".css", ".js", ".sh", ".ts", ".csv", ".jpeg", ".jpg", ".gif", 
    ".png", ".tar", ".xlsx", ".xml", ".zip"
]

class Chat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="chat")
    async def chat(self, int: discord.Interaction,
            assistant_id: str = "Not selected",
            thread_id: str = None, search: str = ''):
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
            if assistant_id == "Not selected":
                name = "Unknown"
            else:
                assistant = await get_assistant(assistant_id)
                name = assistant.name
            embed.add_field(name="thread_id", value=thread_id)
            embed.add_field(name="assistant_id", value=assistant_id)
            embed.add_field(name="name", value=name)
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
            assistants = await search_assistants(search=search)
            for assistant in assistants:
                view.selectMenu.add_option(
                    label=assistant.name if assistant.name is not None else "Unknown",
                    value=assistant.id,
                    description=assistant.description[0:min([100,
                            len(assistant.description)])] if assistant.description is not None else "No description",
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
                first_message = await thread.parent.fetch_message(thread.id)
                openai_thread_id = first_message.embeds[0].fields[0].value
                openai_assistant_id = first_message.embeds[0].fields[1].value
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
                attachments = None
                if message.attachments:
                    attachments = list()
                    for attachment in message.attachments:
                        # Handle the attachment
                        if (os.path.splitext(attachment.filename)[1] in FILE_SEARCH_EXTENSION 
                            or os.path.splitext(attachment.filename)[1] in CODE_INTERPRETER_EXTENSION):
                            pseudo_file = ( 
                                attachment.filename, 
                                await attachment.read(), 
                                attachment.content_type
                            )
                            file_id = await upload_file(file=pseudo_file)
                            attachment_obj = {
                                "file_id": file_id,
                                "tools": [],
                            }
                            if os.path.splitext(attachment.filename)[1] in FILE_SEARCH_EXTENSION:
                                attachment_obj["tools"].append({"type": "file_search"})
                            if os.path.splitext(attachment.filename)[1] in CODE_INTERPRETER_EXTENSION:
                                attachment_obj["tools"].append({"type": "code_interpreter"})
                            attachments.append(attachment_obj)

                # Generate the response
                response_data = await generate_response(
                    thread_id=openai_thread_id,
                    assistant_id=openai_assistant_id,
                    new_message=MessageCreate.from_discord_message(
                        thread_id=openai_thread_id,
                        author_name=message.author.display_name,
                        message=message.content,
                        attachments=attachments,
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
        starter_message = await self.thread.parent.fetch_message(self.thread.id)
        embed = starter_message.embeds[0]
        embed.set_field_at(-2, name="assistant_id", value=selected)
        assistant = await get_assistant(selected)
        embed.set_field_at(-1, name="name", value=assistant.name)
        await starter_message.edit(embed=embed)

class FunctionSelectView(View):
    def __init__(self, *, thread: discord.Thread = None):
        super().__init__()
        self.thread = thread
        self.event = asyncio
        self.selected_function = None
        
    @discord.ui.select(cls=Select, placeholder="Not selected")
    async def selectMenu(self, int: discord.Interaction, select: Select):
        self.selected_function = select.values[0]
        for option in select.options:
            if option.value == self.selected_function:
                option.default = True
                break

        select.disabled = True
        await int.response.edit_message(view=self)

        # modify the starter embed in the thread
        embed = self.thread.starter_message.embeds[0]
        embed.add_field(name="selected_function", value=self.selected_function)
        await self.thread.starter_message.edit(embed=embed)
        self.stop()

# TODO: remove unused args
async def process_response(thread: discord.Thread, response_data: ResponseData) -> None:
    status = response_data.status
    message = response_data.message
    status_text = response_data.status_text

    if status is ResponseStatus.OK:
        sent_message = None
        if not message:
            sent_message = await thread.send(
                embed=discord.Embed(
                    description=f"**Invalid response** - empty response",
                    color=discord.Color.yellow(),
                )
            )
        else:
            messages_rendered = await message.render()
            for message_rendered in messages_rendered:
                shorter_response = split_into_shorter_messages(message_rendered.content)
                for i, response in enumerate(shorter_response):
                    # Send attachments with last message
                    if i == len(shorter_response) - 1:
                        message_rendered.content = response
                        sent_message = await thread.send(**message_rendered.asdict())
                    else:
                        sent_message = await thread.send(response)

    else:
        await thread.send(
            embed=discord.Embed(
                description=f"**Error** - {status_text}",
                color=discord.Color.yellow(),
            )
        )


async def setup(bot):
    await bot.add_cog(Chat(bot))