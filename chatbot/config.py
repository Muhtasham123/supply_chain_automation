"""
Chatbot configuration.

Secrets are loaded from the environment / a .env file at the project root -
nothing sensitive is hardcoded here (see .env.example for the template).

Set your key in .env:

    OPENAI_API_KEY=<paste-your-openai-key-here>
    OPENAI_MODEL=gpt-4o-mini      # optional, this is the default

You can also set OPENAI_API_KEY as a real environment variable or type it into
the app sidebar; any of those work.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# OpenAI API key - read from the environment (.env). Empty by default so no
# secret ever lives in source. Get one from https://platform.openai.com/api-keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# OpenAI chat model. "gpt-4o-mini" is cheap and plenty for text-to-SQL.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
