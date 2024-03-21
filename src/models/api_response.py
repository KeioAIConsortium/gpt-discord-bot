from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from openai import AsyncOpenAI

from src.models.message import Message

logger = logging.getLogger(__name__)

client = AsyncOpenAI()


class ResponseStatus(Enum):
    OK = 0
    ERROR = 1


@dataclass
class ResponseData:
    status: ResponseStatus
    message: Message | None
    status_text: str | None
