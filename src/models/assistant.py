from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

from openai.types.beta.assistant import Assistant as OpenAIAssistant
from src.constants import DEFAULT_MODEL

logger = logging.getLogger(__name__)


@dataclass
class Assistant:
    id: str | None = None
    created_at: int | None = None
    name: str | None = None
    description: str | None = None
    model: str | None = None
    instructions: str | None = None
    tools: list[dict[str, str]] | None = None
    file_ids: list[str] | None = None
    metadata: dict[str, str] | None = None

    def input_to_api_create(self) -> dict[str, str]:
        """Convert the Assistant object to dict for input to API create"""
        tmp = asdict(self, dict_factory=lambda x: {k: v for (k, v) in x if v is not None})
        # model is required for create
        if "model" not in tmp:
            logger.warning("model is required for create. Use default model.")
            tmp["model"] = DEFAULT_MODEL
        # id and created_at are not needed for create
        remove_keys = ["id", "created_at"]
        for key in remove_keys:
            if key in tmp:
                del tmp[key]
        return tmp

    def input_to_api_update(self) -> dict[str, str]:
        """Convert the Assistant object to dict for input to API update"""
        tmp = asdict(self, dict_factory=lambda x: {k: v for (k, v) in x if v is not None})
        # id is required with the key "assistant_id" for update
        if "id" not in tmp:
            raise ValueError("id is required for update")
        tmp["assistant_id"] = tmp.pop("id")
        # created_at is not needed for update
        remove_keys = ["created_at"]
        for key in remove_keys:
            if key in tmp:
                del tmp[key]
        return tmp

    def render(self) -> str:
        """Render the Assistant object to string to display in discord"""
        return f"[{self.id}] {self.name} - {self.description}" + "\n"

    @classmethod
    def from_api_output(cls, api_output: OpenAIAssistant) -> None:
        """Create an instance from the OpenAIAssistant object
        - Convert the OpenAIAssistant object to dict
        - Remove the key "object" from the dict
        """
        return cls(**api_output.model_dump(exclude=["object"]))
