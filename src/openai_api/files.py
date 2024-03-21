from openai import AsyncOpenAI
from src.openai_api.assistants import get_assistant


async def upload_file(file, purpose: str = "assistants") -> str:
    client = AsyncOpenAI()
    openai_file = await client.files.create(
        file=file,
        purpose=purpose,
    )
    return openai_file.id

async def get_image_file(file_id: str) -> bytes:
    client = AsyncOpenAI()
    image_data = await client.files.content(file_id=file_id)
    image_data_bytes = image_data.read()
    return image_data_bytes