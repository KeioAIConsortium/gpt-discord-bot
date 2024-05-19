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
import json

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
    content: str
    role: str = "user"
    attachments: list[dict[str, str|list[dict[str, str]]]] | None = None
    metadata: dict[str, str] | None = None

    @classmethod
    def from_discord_message(
        self, thread_id: str, author_name: str, message: str, attachments: list[dict[str, str|list[dict[str, str]]]] | None = None
    ) -> MessageCreate:
        """Create an instance from the discord message"""
        content = f"{author_name}: {message}"
        return self(thread_id=thread_id, content=content, attachments=attachments)

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
                rendered += content.render()
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

    def render(self) -> list[DiscordMessage]:
        """Render the ContentText object to list of DiscordMessage Object"""
        # TODO: fix render annotations
        # TODO: add File Download via URL
        # Get the text
        waiting_processing_stack = deque()
        rendered = []
        initial_message = DiscordMessage(
            content=self.value,
            files=[],
        )
        waiting_processing_stack.append(initial_message)
        while waiting_processing_stack:
            print(f'[Deb]->len(waiting_processing_stack): {len(waiting_processing_stack)}')
            processing_message = waiting_processing_stack.pop()
            processing_text = processing_message.content
            processing_message_attachments = processing_message.files
            
            # Process the display formula
            # TODO: Detect `$$` pattern
            display_pattern = r'\\\[([\w\s\^_.,=+\-*/{}\[\]()<>!&#:;\|\'\\]+?)\\\]'
            display_match = re.search(display_pattern, processing_text, re.DOTALL)
            if display_match:
                # Get the formula and the text before and after the formula
                pre_text = processing_text[:display_match.start()]
                formula = display_match.group(1)
                post_text = processing_text[display_match.end():]

                # Process the message from back to front to keep the order in the stack
                # Create discord message of text after the formula
                if post_text:
                    print(f'[Deb]->post_text: {post_text}')
                    post_message = DiscordMessage(
                        content=post_text,
                        files=processing_message_attachments, # Processing attachments are passed to the post message
                    )
                    waiting_processing_stack.append(post_message)
                
                # Create discord message of the formula
                if formula:
                    print(f'[Deb]->formula: {formula}')
                    # Convert the formula to latex style
                    formula = re.sub(r'[\n\t]', '', formula)
                    formula = '$' + formula + '$'
                    # Convert the latex style formula to image
                    plt.figure(figsize=(1, 1))
                    plt.text(0.5, 0.5, formula, fontsize=24, ha='center', va='center', color='white')
                    plt.axis('off')
                    pseudo_file = BytesIO()
                    plt.savefig(
                        pseudo_file,
                        format='png',
                        transparent=True,
                        bbox_inches='tight',
                        pad_inches=0
                    )
                    plt.clf()
                    pseudo_file.seek(0)
                    formula_image = File(fp=pseudo_file, filename="formula.png")
                    formula_message = DiscordMessage(
                        content="",
                        files=[formula_image],
                    )
                    waiting_processing_stack.append(formula_message)
                # Create discord message of text before the formula
                if pre_text:
                    print(f'[Deb]->pre_text: {pre_text}')
                    pre_message = DiscordMessage(
                        content=pre_text,
                        files=[],
                    )
                    waiting_processing_stack.append(pre_message)
                # Continue the loop to process the message in step by step
                continue

            if process_inline_formula:
                # Process the inline formula
                # TODO: Detect `$` pattern
                inline_pattern = r'\\\([\w\s\^_.,=+\-*/{}\[\]()<>!&#:;\|\'\\]+?\\\)'
                inline_match = re.search(inline_pattern, processing_text, re.DOTALL)
                if inline_match:
                    # Get the a line with inline formula and the text before and after the formula
                    preline_pos = processing_text.rfind('\n', 0, inline_match.start())
                    postline_pos = processing_text.find('\n', inline_match.end())
                    
                    pre_line = processing_text[:preline_pos].strip() if preline_pos != -1 else ''
                    line_with_formula = processing_text[preline_pos+1:postline_pos if postline_pos != -1 else None].strip()
                    post_line = processing_text[postline_pos+1:].strip() if postline_pos != -1 else ''
                
                    # Create discord message of line after inline formula
                    if post_line:
                        print(f'[Deb]->post_line: {post_line}')
                        post_message = DiscordMessage(
                            content=post_line,
                            files=processing_message_attachments, # Processing attachments are passed to the post message
                        )
                        waiting_processing_stack.append(post_message)
                    
                    # Create discord message of inline formula
                    inline_formulas = set(re.findall(inline_pattern, line_with_formula))
                    print(f'[Deb]->inline_formulas: {inline_formulas}')
                    if inline_formulas:
                        # Modify the text to replace the inline formula with latex style
                        modified_line = line_with_formula
                        for original_formula in inline_formulas:
                            modified_formula = original_formula.replace("\\(", "$").replace("\\)", "$")
                            modified_line = modified_line.replace(original_formula, modified_formula)
                        print(f'[Deb]->modified_line: {modified_line}')
                        # Convert the modified text to the image to display in Discord
                        plt.figure(figsize=(1, 1))
                        plt.text(0.01, 0.99,  modified_line, wrap=True, fontsize=18, ha='left', va='top', color='white')
                        plt.axis('off')
                        pseudo_file = BytesIO()
                        plt.savefig(
                            pseudo_file,
                            format='png',
                            transparent=True,
                            pad_inches=0.1,
                            bbox_inches='tight',
                        )
                        plt.clf()
                        pseudo_file.seek(0)
                        inline_formula_image = File(fp=pseudo_file, filename="message.png")
                        # Create the discord message of the inline formula
                        inline_formula_message = DiscordMessage(
                            content="",
                            files=[inline_formula_image],
                        )
                        waiting_processing_stack.append(inline_formula_message)
                    # Create the discord message of line before inline formula
                    if pre_line:
                        print(f'[Deb]->pre_line: {pre_line}')
                        post_message = DiscordMessage(
                            content=pre_line,
                            files=processing_message_attachments, # Processing attachments are passed to the post message
                        )
                        waiting_processing_stack.append(post_message)
                    continue

            # If there is nothing to process, add the message to the rendered list
            rendered.append(processing_message)
            print(f'[Deb]->len(text.rendered): {len(rendered)}')

        if self.annotations:
            for annotation in self.annotations:
                message = DiscordMessage(
                    content=annotation.render(),
                )
                rendered.append(message)
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
