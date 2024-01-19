import asyncio
import logging

from openai import AsyncOpenAI
from openai.types.beta.thread import Thread as OpenAIThread
from src.models.api_responce import ResponceData, ResponceStatus
from src.models.message import Message, MessageCreate

logger = logging.getLogger(__name__)
client = AsyncOpenAI()


async def create_thread() -> OpenAIThread:
    thread = await client.beta.threads.create()
    return thread


# TODO: only support 1 message to add. If we want to add multiple messages, we need change input to list
async def add_user_message_to_thread(cfg: MessageCreate) -> Message:
    responce = await client.beta.threads.messages.create(**cfg.input_to_api_create())
    return Message.from_api_output(responce)


async def generate_assistant_message_in_thread(thread_id: str, assistant_id: str) -> ResponceData:
    try:
        run = await client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
        # TODO: check the run status periodically
        while run.status != "completed":
            if run.status == "cancelled":  # ending states (not error)
                logger.info(f"Run {run.status}")
                return ResponceData(
                    status=ResponceStatus.OK,
                    content=None,
                    status_text=f"Run {run.status}",
                )
            elif run.status in ["cancelled", "expired", "failed"]:  # ending states (error)
                logger.info(f"Run {run.status}")
                return ResponceData(
                    status=ResponceStatus.ERROR,
                    content=None,
                    status_text=f"Run {run.status}",
                )

            await asyncio.sleep(1)
            run = await client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        # If the run is completed, retreive the last message the assistant sent
        desc_thread_messages = await client.beta.threads.messages.list(thread_id)
        last_message = desc_thread_messages.data[0]
        last_message = Message.from_api_output(last_message)

        if last_message.role == "assistant":
            return ResponceData(
                status=ResponceStatus.OK,
                content=last_message.content,
                status_text=None,
            )
        else:
            return ResponceData(
                status=ResponceStatus.ERROR,
                content=None,
                status_text=f"No response from assistant",
            )

    # TODO: need error handling?: https://platform.openai.com/docs/guides/error-codes/python-library-error-types
    except Exception as e:
        logger.exception(e)
        return ResponceData(status=ResponceStatus.ERROR, content=None, status_text=str(e))


async def generate_response(
    thread_id: str, assistant_id: str, new_message: MessageCreate
) -> ResponceData:
    assert thread_id == new_message.thread_id
    _ = await add_user_message_to_thread(new_message)
    responce_data = await generate_assistant_message_in_thread(
        thread_id=thread_id, assistant_id=assistant_id
    )
    return responce_data
