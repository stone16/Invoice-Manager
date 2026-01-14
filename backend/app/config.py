from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/invoice_db"

    # LLM Provider Configuration
    # Supported providers: openai, anthropic, google, qwen, deepseek, zhipu
    llm_provider: str = ""  # Active provider (empty = not configured)

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = ""  # Custom base URL (for OpenAI-compatible APIs)

    # Anthropic (Claude)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-haiku-20240307"

    # Google (Gemini)
    google_api_key: str = ""
    google_model: str = "gemini-1.5-flash"

    # Qwen (Alibaba)
    qwen_api_key: str = ""
    qwen_model: str = "qwen-turbo"
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"

    # Zhipu (GLM)
    zhipu_api_key: str = ""
    zhipu_model: str = "glm-4-flash"

    # File upload
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: list[str] = ["pdf", "jpg", "jpeg", "png"]

    # Parallel processing settings
    # Separate pools for OCR and LLM to maximize throughput
    # OCR is CPU-bound (image processing), limit based on available cores
    # LLM is I/O-bound (API calls), can handle more concurrent requests
    ocr_max_workers: int = 8   # CPU-bound: ~2x typical core count
    llm_max_workers: int = 15  # I/O-bound: limited by API rate limits

    # App
    debug: bool = True

    model_config = SettingsConfigDict(env_file=".env")

    def get_active_llm_provider(self) -> Optional[str]:
        """Get the active LLM provider based on configuration."""
        # If explicitly set, use that
        if self.llm_provider:
            return self.llm_provider

        # Auto-detect based on available API keys
        if self.openai_api_key:
            return "openai"
        if self.anthropic_api_key:
            return "anthropic"
        if self.google_api_key:
            return "google"
        if self.qwen_api_key:
            return "qwen"
        if self.deepseek_api_key:
            return "deepseek"
        if self.zhipu_api_key:
            return "zhipu"

        return None

    def is_llm_configured(self) -> bool:
        """Check if any LLM provider is configured."""
        return self.get_active_llm_provider() is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache():
    """Clear the settings cache to reload from environment."""
    get_settings.cache_clear()
