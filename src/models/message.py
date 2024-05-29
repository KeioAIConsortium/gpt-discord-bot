from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, List, Optional, Dict, TypedDict, Literal

from openai.types.beta.threads import (
    Message as OpenAIThreadMessage,
)

from discord import (
    Embed, File, AllowedMentions
)

from src.openai_api.files import get_image_file

from io import BytesIO
import re
from matplotlib import (
    pyplot as plt,
    font_manager,
)
import matplotlib
import shutil
from collections import deque
import os
# from openai.types.beta.threads.text_content_block_param import TextContentBlockParam
# from openai.types.beta.threads.image_url_content_block_param import ImageURLContentBlockParam
# from openai.types.beta.threads.image_file_content_block_param import ImageFileContentBlockParam

logger = logging.getLogger(__name__)

# Set the font to use in matplotlib
# TODO: Install Latex Engine
font_name = os.getenv('LATEX_FONT', 'DejaVu Sans')
# Check if the font is available
available_fonts = [f.name for f in font_manager.fontManager.ttflist]
if font_name in available_fonts:
    # Set the font
    plt.rcParams['font.family'] = font_name
    print(f"Font '{font_name}' is found and set successfully.")
else:
    # Remove the cache file to avoid the error
    shutil.rmtree(matplotlib.get_cachedir())
    print("The font cannnot be loaded. Please try again after install it.")
    print("If it is installed, this error may be caused by cache file and it was removed now.")
    print("Please excute this program again.")

process_inline_formula = False # os.getenv('PROCESS_INLINE_FORMULA', 'False').lower() == 'true'

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
    content: str | List[dict[str, ContentText|str] | dict[str, ContentImageFile|str]]
    role: str = "user"
    attachments: list[dict[str, str|list[dict[str, str]]]] | None = None
    metadata: dict[str, str] | None = None

    @classmethod
    def from_discord_message(
        self, thread_id: str, author_name: str, message: str, image_ids: list[str], attachments: list[dict[str, str|list[dict[str, str]]]] | None = None
    ) -> MessageCreate:
        """Create an instance from the discord message"""
        message = f"{author_name}: {message}"
        content = [
            {
                "image_file" : 
                    {
                        "file_id" : image_id,
                        "detail" : "auto"
                    },
                "type" : "image_file"
            } for image_id in image_ids
        ] if image_ids else []
        content.append({
            "text" : message,
            "type" : "text"
        })
        return self(thread_id=thread_id, content=content, attachments=attachments)

    def input_to_api_create(self) -> dict[str, str]:
        """Convert the MessageCreate object to dict for input to API create"""
        dict = asdict(self, dict_factory=lambda x: {k: v for (k, v) in x if v is not None})
        print("[Deb]->MessageCreate: ", dict)
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
    attachments: list[dict[str, str|list[dict[str, str]]]] | None = None

    @classmethod
    def from_api_output(cls, api_output: OpenAIThreadMessage) -> None:
        """Create an instance from the OpenAIThreadMessage object
        - Convert the OpenAIThreadMessage object to dict
        - Remove the key "object" from the dict
        """
        dct = api_output.model_dump(exclude=[
            "object", 
            "completed_at", 
            "incomplete_at", 
            "incomplete_details", 
            "status",
            "metadata",
        ])
        print("[Deb]->Message: ", dct)
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
        print("[Deb]->contents_converted: ", contents_converted)

        return cls(content=contents_converted, **dct)

    async def render(self) -> list[DiscordMessage]:
        """
        Render the Message object to the list of DiscordMessage object
        """
        # the list of DiscordMessage object to return
        rendered = []

        # Render the content based on the type
        for content in self.content:
            # Text content
            if type(content) == ContentText:
                rendered += await content.render()
            # Image content
            elif type(content) == ContentImageFile:
                if rendered:
                    message = await content.render()
                    rendered[-1].files += message.files
                else:
                    rendered.append(await content.render())
        print("[Deb]->rendered message: ", str(rendered))
        return rendered

@dataclass
class ContentText:
    value: str | None = None
    annotations: list[AnnotationFilePath] | None = None

    @classmethod
    def from_api_output(cls, api_output: dict[str, Any]) -> ContentText:
        annotations_dct = api_output.pop("annotations")
        annotations = None
        if annotations_dct is not None:
            annotations = []
            for annotation in annotations_dct:
                if annotation["type"] == "file_path":
                    annotations.append(
                        AnnotationFilePath.from_api_output(annotation)
                    )
                    print("[Deb]->annotations: ", annotations)
                else:
                    # TODO: handle another annotation type
                    logger.warning(f"Unknown annotation type: {annotation['type']}")
        return cls(value=api_output["value"], annotations=annotations)

    async def render(self) -> list[DiscordMessage]:
        """Render the ContentText object to list of DiscordMessage Object"""
        # TODO: fix render annotations
        rendered = []
        
        # Get the text        
        processing_text = self.value
        
        # Replace display formulas
        display_pattern = r'\\\[([\w\s\^_.,=+\-*/{}\[\]()<>!&#:;\|\'\\]+?)\\\]'
        processing_text = re.sub(
            display_pattern, 
            lambda match: 
                '$$' + match.group(1).replace('\n', '').replace('\t', '').replace('\\\\', '\\\\\\\\') 
                + '$$', processing_text, flags=re.DOTALL
        )
        
        # Replace inline formulas
        inline_pattern = r'\\\(([\w\s\^_.,=+\-*/{}\[\]()<>!&#:;\|\'\\]+?)\\\)'
        processing_text = re.sub(
            inline_pattern, 
            lambda match: '$' + match.group(1).replace('\n', '').replace('\t', '').replace('\\\\', '\\\\\\\\') 
            + '$', processing_text, flags=re.DOTALL
        )

        # Create the discord message fpr the processing text
        discord_message = DiscordMessage(
            content=processing_text,
        )
        rendered.append(discord_message)

        # Render the annotations
        if self.annotations is not None:
            for annotation in reversed(self.annotations):
                message = await annotation.render()
                rendered.append(message)

        print(f'[Deb]->len(text.rendered): {len(rendered)}')

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

    async def render(self) -> DiscordMessage:
        """Render the ContentAnnotation object to string to display in discord"""
        image_file = await get_image_file(self.file_path['file_id'])
        message = DiscordMessage(
            content=f"",
            files=[File(fp=BytesIO(image_file), filename="output_image.png")],
        )
        return message

@dataclass
class ContentImageFile:
    file_id: str | None = None
    detail: str | None = None

    @classmethod
    def from_api_output(cls, api_output: dict[str, Any]) -> ContentImageFile:
        return cls(**api_output)

    async def render(self) -> DiscordMessage:
        """Render the ContentImageFile object to DiscordMessage object"""
        image_bytes = await get_image_file(self.file_id)
        pseudo_file = BytesIO(image_bytes)
        discord_file = File(fp=pseudo_file, filename="output_image.png")
        rendered = DiscordMessage(
            content="",
            files=[discord_file],
        )
        return rendered


class ParameterSchema(TypedDict):
    type: str
    description: str


class FunctionParameters(TypedDict):
    type: str
    properties: Dict[str, ParameterSchema]
    required: list[str]


class FunctionDefinition(TypedDict, total=False):
    name: str
    description: str
    parameters: FunctionParameters


class FunctionTool(TypedDict):
    function: FunctionDefinition
    type: Literal["function"]


def create_function(
    name: str,
    description: str,
    parameters: Dict[str, ParameterSchema],
    required_parameters: list[str],
) -> FunctionTool:
    function_params = {
        "type": "object",
        "description": description,
        "properties": parameters,
        "required": required_parameters,
    }

    function_definition: FunctionDefinition = {
        "name": name,
        "description": description,
        "parameters": function_params,
    }

    return {
        "function": function_definition,
        "type": "function",
    }

def function_tool_to_dict(func_tool: FunctionTool) -> dict[str, Any]:
    return {
        "type": func_tool["type"],
        "function": func_tool["function"],
    }
