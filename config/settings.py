import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve the .env file relative to this file's location, not the CWD.
# This ensures load_dotenv works correctly regardless of where the script
# or Streamlit server is launched from.
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

# Export keys for easy import across the app
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# NOTE: We intentionally do NOT raise here at import time.
# A module-level raise crashes the Streamlit process before any UI renders.
# Individual agents and tools perform their own key presence checks at
# invocation time, allowing the UI to surface a user-friendly error message.