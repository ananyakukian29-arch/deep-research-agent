import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dynamically resolve the absolute path to the root directory
# __file__ is backend/config.py. dirname gets 'backend', dirname again gets the root.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE_PATH = os.path.join(ROOT_DIR, ".env")

class Settings(BaseSettings):
    GROQ_API_KEY: str
    TAVILY_API_KEY: str
    MONGO_URI: str = "mongodb://127.0.0.1:27017/"
    MONGO_DB_NAME: str = "deep_research_db"
    REDIS_URL: str = "redis://127.0.0.1:6379/0" # Setting a safer default

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()