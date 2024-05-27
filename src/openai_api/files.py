from openai import AsyncOpenAI
from openai._types import FileTypes
from src.openai_api.assistants import get_assistant


async def upload_file(file:FileTypes, purpose: str = "assistants") -> str:
    client = AsyncOpenAI()
    openai_file = await client.files.create(
        file=file,
        purpose=purpose,
    )
    return openai_file.id

async def create_vector_store(name: str, file_ids:list[str]|None=None) -> str:
    client = AsyncOpenAI()
    if file_ids is None:
        vector_store = await client.beta.vector_stores.create(
            name=name,
        )
    else:
        vector_store = await client.beta.vector_stores.create(
            name=name,
            file_ids=file_ids,
        )
    return vector_store.id

async def update_vector_store(vector_store_id: str, file:FileTypes) -> str:
    client = AsyncOpenAI()
    vector_store = await client.beta.vector_stores.files.upload(
        vector_store_id=vector_store_id,
        file=file,
    )
    return vector_store.id

async def get_image_file(file_id: str) -> bytes:
    client = AsyncOpenAI()
    image_data = await client.files.content(file_id=file_id)
    image_data_bytes = image_data.read()
    return image_data_bytes