import asyncio
import logging

from openai import AsyncOpenAI
from openai.types.beta.thread import Thread as OpenAIThread

from src.models.api_response import ResponseData, ResponseStatus
from src.models.message import Message, MessageCreate

logger = logging.getLogger(__name__)
client = AsyncOpenAI()


async def create_thread() -> OpenAIThread:
    thread = await client.beta.threads.create()
    return thread


# TODO: only support 1 message to add. If we want to add multiple messages, we need change input to list
async def add_user_message_to_thread(cfg: MessageCreate) -> Message:
    response = await client.beta.threads.messages.create(**cfg.input_to_api_create())
    return Message.from_api_output(response)


async def generate_assistant_message_in_thread(thread_id: str, assistant_id: str) -> ResponseData:
    try:
        run = await client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
        # TODO: check the run status periodically
        while run.status != "completed":
            if run.status == "cancelled":  # ending states (not error)
                logger.info(f"Run {run.status}")
                return ResponseData(
                    status=ResponseStatus.OK,
                    message=None,
                    status_text=f"Run {run.status}",
                )
            elif run.status in ["cancelled", "expired", "failed"]:  # ending states (error)
                logger.info(f"Run {run.status}")
                return ResponseData(
                    status=ResponseStatus.ERROR,
                    message=None,
                    status_text=f"Run {run.status}",
                )

            await asyncio.sleep(1)
            run = await client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        # If the run is completed, retreive the last message the assistant sent
        desc_thread_messages = await client.beta.threads.messages.list(thread_id)
        last_message = desc_thread_messages.data[0]
        last_message = Message.from_api_output(last_message)

        if last_message.role == "assistant":
            return ResponseData(
                status=ResponseStatus.OK,
                message=last_message,
                status_text=None,
            )
        else:
            return ResponseData(
                status=ResponseStatus.ERROR,
                message=None,
                status_text=f"No response from assistant",
            )

    # TODO: need error handling?: https://platform.openai.com/docs/guides/error-codes/python-library-error-types
    except Exception as e:
        logger.exception(e)
        return ResponseData(
            status=ResponseStatus.ERROR, 
            message=None, 
            status_text=str(e)
        )


async def generate_response(
    thread_id: str, assistant_id: str, new_message: MessageCreate
) -> ResponseData:
    assert thread_id == new_message.thread_id
    _ = await add_user_message_to_thread(new_message)
    response_data = await generate_assistant_message_in_thread(
        thread_id=thread_id, assistant_id=assistant_id
    )
    return response_data
