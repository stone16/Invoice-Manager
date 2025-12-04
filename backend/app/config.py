from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/invoice_db"

    # OpenAI (optional)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # File upload
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: list[str] = ["pdf", "jpg", "jpeg", "png"]

    # App
    debug: bool = True

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
