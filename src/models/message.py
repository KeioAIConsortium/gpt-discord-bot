from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, List, Optional

from openai.types.beta.threads import (
    Message as OpenAIThreadMessage,
)

from discord import (
    Embed, File, AllowedMentions
)

from src.openai_api.files import get_image_file
from io import BytesIO

logger = logging.getLogger(__name__)

@dataclass
class DiscordMessage:
    content: Optional[str] = None
    tts: Optional[bool] = None
    embed: Optional[Embed] = None
    embeds: Optional[List[Embed]] = None
    file: Optional[File] = None
    files: Optional[List[File]] = None
    nonce: Optional[int] = None
    delete_after: Optional[float] = None
    allowed_mentions: Optional[AllowedMentions] = None

    def asdict(self) -> dict[str, str]:
        """Convert the MessageCreate object to dict"""
        return asdict(self, dict_factory=lambda x: {k: v for (k, v) in x if v is not None})

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
        dct = api_output.model_dump(exclude=["object", "completed_at", "incomplete_at", "incomplete_details", "status"])
        contents_dct = dct.pop("content")
        contents_converted = []
        for content_dct in contents_dct:
            if content_dct["type"] == "text":
                contents_converted.append(
                    ContentText.from_api_output(content_dct["text"])
                )
            elif content_dct["type"] == "image_file":
                contents_converted.append(
                    ContentImageFile.from_api_output(content_dct["image_file"])
                )
            else:
                logger.warning(f"Unknown content type: {content_dct['type']}")

        return cls(content=contents_converted, **dct)

    async def render(self) -> DiscordMessage:
        """
        Render the Message object to DiscordMessage object
        """
        rendered = DiscordMessage(
            content="",
            files=[],
        )
        for content in self.content:
            if type(content) == ContentText:
                rendered.content += content.render() + "\n"
            elif type(content) == ContentImageFile:
                rendered.files.append(await content.render())
        return rendered

@dataclass
class ContentText:
    value: str | None = None
    annotations: list[AnnotationFilePath] | None = None

    @classmethod
    def from_api_output(cls, api_output: dict[str, Any]) -> ContentText:
        annotations_dct = api_output.pop("annotations")
        annotations_converted = []
        for annotation in annotations_dct:
            if annotation["type"] == "file_path":
                annotations_converted.append(
                    AnnotationFilePath.from_api_output(annotation)
                )
            else:
                # TODO: handle another annotation type
                logger.warning(f"Unknown annotation type: {annotation['type']}")
        return cls(**api_output)

    def render(self) -> str:
        """Render the ContentText object to string to display in discord"""
        # TODO: fix render annotations
        rendered = self.value
        if self.annotations:
            for annotation in self.annotations:
                rendered += f"\n{annotation.render()}"
        return rendered

@dataclass
class AnnotationFilePath:
    type: str | None = None
    text: str | None = None
    start_index: int | None = None
    end_index: int | None = None
    file_path: dict[str, str] | None = None

    @classmethod
    def from_api_output(cls, api_output: dict[str, Any]) -> AnnotationFilePath:
        return cls(**api_output)

    def render(self) -> str:
        """Render the ContentAnnotation object to string to display in discord"""
        # TODO: render file path
        return f"Annotation File Path {self.start}-{self.end}: {self.file_path['file_id']}"

@dataclass
class ContentImageFile:
    file_id: str | None = None

    @classmethod
    def from_api_output(cls, api_output: dict[str, Any]) -> ContentImageFile:
        return cls(**api_output)

    async def render(self) -> File:
        """Render the ContentImageFile object to discord File object"""
        image_bytes = await get_image_file(self.file_id)
        psuedo_file = BytesIO(image_bytes)
        discord_file = File(fp=psuedo_file, filename="output_image.png")
        return discord_file
