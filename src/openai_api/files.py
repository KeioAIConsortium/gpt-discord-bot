from openai import AsyncOpenAI
from src.openai_api.assistants import get_assistant


async def upload_file(file, purpose: str = "assistants") -> str:
    client = AsyncOpenAI()
    openai_file = await client.files.create(
        file=file,
        purpose=purpose,
    )
    return openai_file.id