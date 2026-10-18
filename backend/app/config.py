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

    # Storage and LLM settings
    DATA_DIR: str = "./data"
    CHROMA_DIR: str = "./data/chroma"
    CHECKPOINT_DB_PATH: str = "./data/checkpoints.sqlite"
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    LLM_TIMEOUT_SECONDS: int = 20
    LLM_MAX_RETRIES: int = 2
    BOOKING_TIMEZONE: str = "Asia/Kolkata"

    # RAG & Handbook Ingestion settings
    HANDBOOK_URL: str = "https://raw.githubusercontent.com/example/handbook/main/employee_handbook.pdf"
    HANDBOOK_FILENAME: str = "employee_handbook.pdf"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    RETRIEVAL_TOP_K: int = 4
    RETRIEVAL_MAX_DISTANCE: float = 0.55

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
