"""

"""


from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME:   str = "Life Dash"
    OBSIDIAN_PATH:  Path
    DATABASE_URL:   str
    DEBUG:          bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
