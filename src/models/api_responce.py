from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from openai import AsyncOpenAI

from src.models.message import ContentImageFile, ContentText

logger = logging.getLogger(__name__)

client = AsyncOpenAI()


class ResponceStatus(Enum):
    OK = 0
    ERROR = 1


@dataclass
class ResponceData:
    status: ResponceStatus
    content: list[ContentImageFile | ContentText] | None
    status_text: str | None
