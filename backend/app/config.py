"""Configuration settings for Agentic Handbook Assistant."""

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "dev"
    VERSION: str = "0.1.0"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:5173"]

    # Storage and LLM defaults for upcoming phases
    DATA_DIR: str = "./data"
    CHROMA_DIR: str = "./data/chroma"
    CHECKPOINT_DB_PATH: str = "./data/checkpoints.sqlite"
    LLM_PROVIDER: str = "groq"
    BOOKING_TIMEZONE: str = "Asia/Kolkata"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
