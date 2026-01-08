from __future__ import annotations

import importlib
import os
import threading
from typing import Any, Optional

from app.config import get_settings

_LANGSMITH_LOCK = threading.Lock()


class LangChainClientFactory:
    """Factory for building LangChain chat models with provider settings."""

    def __init__(self, settings=None):
        """Initialize factory with settings or defaults."""
        self.settings = settings or get_settings()
        self.langsmith_client = None

    def configure_langsmith(self) -> bool:
        """Configure LangSmith environment variables if tracing is enabled."""
        with _LANGSMITH_LOCK:
            return self._configure_langsmith_locked()

    def _configure_langsmith_locked(self) -> bool:
        """Configure LangSmith settings while holding a process lock."""
        if not self.settings.langsmith_tracing or not self.settings.langsmith_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "false"
            self.langsmith_client = None
            return False

        os.environ["LANGCHAIN_API_KEY"] = self.settings.langsmith_api_key
        if self.settings.langsmith_project:
            os.environ["LANGCHAIN_PROJECT"] = self.settings.langsmith_project
        if self.settings.langsmith_endpoint:
            os.environ["LANGCHAIN_ENDPOINT"] = self.settings.langsmith_endpoint

        try:
            module = importlib.import_module("langsmith")
            client_cls = getattr(module, "Client", None)
            if client_cls is None:
                raise RuntimeError("langsmith Client not available")
            self.langsmith_client = client_cls()
        except Exception:
            os.environ["LANGCHAIN_TRACING_V2"] = "false"
            self.langsmith_client = None
            return False

        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        return True

    def build_chat_model(
        self,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ):
        """Build a LangChain chat model for the active provider."""
        self.configure_langsmith()
        provider = self.settings.get_active_llm_provider() if hasattr(self.settings, "get_active_llm_provider") else None
        if not provider:
            provider = "openai"

        if provider in {"openai", "qwen", "deepseek", "zhipu"}:
            return self._build_openai_compatible(provider, model, temperature, max_tokens, **kwargs)

        if provider == "anthropic":
            return self._build_anthropic(model, temperature, max_tokens, **kwargs)
        if provider == "google":
            return self._build_google(model, temperature, max_tokens, **kwargs)

        raise ValueError(f"Unsupported LLM provider: {provider}")

    def _build_openai_compatible(self, provider: str, model, temperature, max_tokens, **kwargs):
        """Build an OpenAI-compatible chat model client."""
        from langchain_openai import ChatOpenAI

        api_key, base_url, model_name = self._resolve_openai_provider(provider, model)
        if not api_key:
            raise ValueError(f"API key missing for provider: {provider}")

        client_kwargs = {"model": model_name, "api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        if temperature is not None:
            client_kwargs["temperature"] = temperature
        if max_tokens is not None:
            client_kwargs["max_tokens"] = max_tokens
        client_kwargs.update(kwargs)
        return ChatOpenAI(**client_kwargs)

    def _build_anthropic(self, model, temperature, max_tokens, **kwargs):
        """Build an Anthropic chat model client."""
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("langchain-anthropic is required for Anthropic support") from exc

        model_name = model or self.settings.anthropic_model
        return ChatAnthropic(
            model=model_name,
            api_key=self.settings.anthropic_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def _build_google(self, model, temperature, max_tokens, **kwargs):
        """Build a Google Gemini chat model client."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("langchain-google-genai is required for Google support") from exc

        model_name = model or self.settings.google_model
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self.settings.google_api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
            **kwargs,
        )

    def _resolve_openai_provider(self, provider: str, model: Optional[str]):
        """Resolve API key, base URL, and model name for a provider."""
        if provider == "qwen":
            return self.settings.qwen_api_key, self.settings.qwen_base_url, model or self.settings.qwen_model
        if provider == "deepseek":
            return self.settings.deepseek_api_key, self.settings.deepseek_base_url, model or self.settings.deepseek_model
        if provider == "zhipu":
            return self.settings.zhipu_api_key, None, model or self.settings.zhipu_model
        return self.settings.openai_api_key, self.settings.openai_base_url, model or self.settings.openai_model
