from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

from openai.types.beta.threads.thread_message import (
    ThreadMessage as OpenAIThreadMessage,
)

logger = logging.getLogger(__name__)


@dataclass
class MessageCreate:
    thread_id: str
    content: str
    role: str = "user"
    file_ids: list[str] | None = None
    metadata: dict[str, str] | None = None

    @classmethod
    def from_discord_message(
        self, thread_id: str, author_name: str, message: str, file_ids: list[str] | None = None
    ) -> MessageCreate:
        """Create an instance from the discord message"""
        content = f"{author_name}: {message}"
        return self(thread_id=thread_id, content=content, file_ids=file_ids)

    def input_to_api_create(self) -> dict[str, str]:
        """Convert the MessageCreate object to dict for input to API create"""
        return asdict(self, dict_factory=lambda x: {k: v for (k, v) in x if v is not None})


@dataclass
class Message:
    id: str | None = None
    created_at: int | None = None
    thread_id: str | None = None
    role: str | None = None
    content: list[ContentImageFile | ContentText] | None = None
    assistant_id: str | None = None
    run_id: str | None = None
    file_ids: list[str] | None = None
    metadata: dict[str, str] | None = None

    @classmethod
    def from_api_output(cls, api_output: OpenAIThreadMessage) -> None:
        """Create an instance from the OpenAIThreadMessage object
        - Convert the OpenAIThreadMessage object to dict
        - Remove the key "object" from the dict
        """
        dct = api_output.model_dump(exclude=["object"])

        contents_dct = dct.pop("content")
        contents_converted = []
        for content_dct in contents_dct:
            if content_dct["type"] == "text":
                contents_converted.append(ContentText.from_api_output(content_dct["text"]))
            elif content_dct["type"] == "image":
                contents_converted.append(
                    ContentImageFile.from_api_output(content_dct["image_file"])
                )

        return cls(content=contents_converted, **dct)

    def render(self) -> str:
        """Render the Message object to string to display in discord"""
        rendered = ""
        for content in self.content:
            rendered += content.render() + "\n"


@dataclass
class ContentText:
    value: str | None = None
    annotations: list | None = None

    @classmethod
    def from_api_output(cls, api_output: dict[str, Any]) -> ContentText:
        return cls(**api_output)

    def render(self) -> str:
        """Render the ContentText object to string to display in discord"""
        # TODO: render annotations
        return self.value


@dataclass
class ContentImageFile:
    file_id: str | None = None

    @classmethod
    def from_api_output(cls, api_output: dict[str, Any]) -> ContentImageFile:
        return cls(**api_output)

    def render(self) -> str:
        """Render the ContentImageFile object to string to display in discord"""
        # TODO: render image
        return f"Image: {self.file_id}"
