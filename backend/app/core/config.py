from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Agentic Industrial Inspection"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # PostgreSQL Database Configuration
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5433/industrial_inspection"

    # LLM Provider Configuration (Local Ollama)
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:latest"
    LLM_REQUEST_TIMEOUT_SECONDS: float = 180.0

    # Future integration settings (placeholders for subsequent phases)
    ANTHROPIC_API_KEY: Optional[str] = None
    MODEL_NAME: Optional[str] = "gemma3:latest"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
