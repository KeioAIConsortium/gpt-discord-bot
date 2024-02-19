# GPT Discord Bot

A Discord bot written in Python that uses the [assistants API](https://platform.openai.com/docs/api-reference/assistants) to have conversations with the `gpt-4` model.

This bot uses the [OpenAI Python Library](https://github.com/openai/openai-python) and [discord.py](https://discordpy.readthedocs.io/).

It is designed to facilitate interactive learning and engagement through group conversations. It is especially suitable for group learning, as making prompts visible in public threads allows everyone in the channel to learn together.

# Features

- `/build` initiates an assistant creation process, with a `name` argument. Users can define the assistant's name, description, and instructions in a guided, interactive thread.

- `/update` initiates an assistant update process, with a `assistant_id` argument. Users can redefine the assistant's description and instructions.

- `/chat` starts a public thread where you can select an assistant for the chat. The assistant will generate a reply for every user message in the thread.

- Each Discord thread is linked to an [OpenAI thread](https://platform.openai.com/docs/api-reference/threads) and an [OpenAI assistant](https://platform.openai.com/docs/api-reference/assistants). Context window management is handled inside the API.

- Supports multi-user interaction. The bot can recognize individual users in a thread and generate responses accordingly.

- You can change the model, the default value is `gpt-4`.


# Setup

1. Clone the repository

    ```bash
    git clone https://github.com/KeioAIConsortium/gpt-discord-bot.git
    cd gpt-discord-bot
    ```

2. Copy `.env.example` to `.env` and start filling in the values as detailed below:

    1. Go to https://beta.openai.com/account/api-keys, create a new API key, and fill in `OPENAI_API_KEY`
    2. Create your own Discord application at https://discord.com/developers/applications
    3. Go to the Bot tab and click "Add Bot"
        - Click "Reset Token" and fill in `DISCORD_BOT_TOKEN`
        - Disable "Public Bot" unless you want your bot to be visible to everyone
        - Enable "Message Content Intent" under "Privileged Gateway Intents"
    4. Go to the OAuth2 tab, copy your "Client ID", and fill in `DISCORD_CLIENT_ID`
    5. Copy the ID the server you want to allow your bot to be used in by right clicking the server icon and clicking "Copy ID". Fill in `ALLOWED_SERVER_IDS`. If you want to allow multiple servers, separate the IDs by "," like `server_id_1,server_id_2`

3. Install dependencies and run the bot

    ```bash
    pip install -r requirements.txt
    python -m src.main
    ```

    You should see an invite URL in the console. Copy and paste it into your browser to add the bot to your server.
    
**Note**: make sure you are using Python 3.9+ (check with `python --version`)


# Usage

The bot operates via slash commands. Type `/` in a text channel to view available commands.

- **`/build`**: Initiates an assistant creation process. Users can define the assistant's name, description, and instructions in a guided, interactive thread.

- **`/update`**: Initiates an assistant update process. Users can redefine the assistant's description and instructions in a guided, interactive thread. If users do not want to change any of these, they can specify '.' to indicate no change.

- **`/list`**: Displays a list of the 20 newest assistants.

- **`/delete`**: Allows users to delete a specified assistant, with confirmations to prevent accidental deletions.

- **`/chat`**: Starts a conversation in a thread. Each new user message is sent as a separate input to the OpenAI API. Users can select an assistant for the chat.


# Acknowledgements

Most of this project were inspired by [OpenAI's official GPT Discord bot](https://github.com/openai/gpt-discord-bot/tree/main).


# Project Status

This project is currently in development.
