from src.models.message import create_function

get_current_temperature = create_function(
    name="get_current_temperature",
    description="Get the current temperature for a specific location",
    parameters={
        "location": {
            "type": "string",
            "description": "The city and state, e.g., San Francisco, CA",
        },
        "unit": {
            "type": "string",
            "enum": ["Celsius", "Fahrenheit"],
            "description": "The temperature unit to use. Infer this from the user's location.",
        },
    },
    required_parameters=["location", "unit"],
)

get_rain_probability = create_function(
    name="get_rain_probability",
    description="Get the probability of rain for a specific location",
    parameters={
        "location": {
            "type": "string",
            "description": "The city and state, e.g., San Francisco, CA",
        },
    },
    required_parameters=["location"],
)


get_wikipedia_summary = create_function(
    name="get_wikipedia_summary",
    description="Search Wikipedia for a summary of a topic",
    parameters={
        "query": {
            "type": "string",
            "description": "The search query to look up on Wikipedia",
        },
    },
    required_parameters=["query"],
)

available_functions = [
    get_current_temperature,
    get_rain_probability,
    get_wikipedia_summary,
]
