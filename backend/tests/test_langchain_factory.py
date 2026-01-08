from __future__ import annotations

import sys
import types

import pytest

from app.services.langchain_client_factory import LangChainClientFactory  # noqa: E402


class DummySettings:
    llm_provider = "openai"
    openai_api_key = "test-key"
    openai_model = "gpt-4o"
    openai_base_url = ""
    qwen_api_key = ""
    qwen_model = "qwen-turbo"
    qwen_base_url = ""
    deepseek_api_key = ""
    deepseek_model = "deepseek-chat"
    deepseek_base_url = ""
    langsmith_api_key = ""
    langsmith_project = ""
    langsmith_endpoint = ""
    langsmith_tracing = False

    def get_active_llm_provider(self):
        return self.llm_provider


def test_build_chat_model_openai(monkeypatch):
    class DummyChatOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    fake_module = types.SimpleNamespace(ChatOpenAI=DummyChatOpenAI)
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_module)

    factory = LangChainClientFactory(DummySettings())
    model = factory.build_chat_model()

    assert isinstance(model, DummyChatOpenAI)
    assert model.kwargs["model"] == "gpt-4o"
    assert model.kwargs["api_key"] == "test-key"


def test_langsmith_fallback_when_unavailable(monkeypatch):
    settings = DummySettings()
    settings.langsmith_tracing = True
    settings.langsmith_api_key = "ls-key"

    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.setitem(sys.modules, "langsmith", None)

    factory = LangChainClientFactory(settings)
    enabled = factory.configure_langsmith()

    assert enabled is False
    assert factory.langsmith_client is None
