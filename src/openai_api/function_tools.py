from src.models.message import create_function
from src.openai_api.functions import get_wikipedia_summary_function
import json


def get_function_tool_outputs(tool_calls):
    tool_outputs = []
    for tool in tool_calls:
        function_dict = tool.function.dict()
        argumants_dict = json.loads(function_dict["arguments"])

        if tool.function.name == "get_wikipedia_summary":
            query = argumants_dict["query"]
            summary = get_wikipedia_summary_function(query)

            if summary:
                tool_outputs.append(
                    {
                        "tool_call_id": tool.id,
                        "output": summary,
                    }
                )

    return tool_outputs

get_wikipedia_summary = create_function(
    name="get_wikipedia_summary",
    description="Search Wikipedia and retrieve a page summary and its URL",
    parameters={
        "query": {
            "type": "string",
            "description": "The search query to look up on Wikipedia",
        },
    },
    required_parameters=["query"],
)


def get_available_functions():
    return available_functions


available_functions = [
    get_wikipedia_summary,
]
