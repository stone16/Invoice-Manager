"""Factory for creating LangChain LLM clients."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


# Default model configuration
DEFAULT_MODEL_CONFIG: Dict[str, Any] = {
    "model": "gpt-4o",
    "temperature": 0.0,
    "max_tokens": 4096,
    "timeout": 120,
}


def build_model_kwargs(model_config: Dict[str, Any]) -> Dict[str, Any]:
    """Build keyword arguments for LangChain model initialization.

    Args:
        model_config: Model configuration dictionary.

    Returns:
        Keyword arguments for model initialization.
    """
    kwargs = {}

    # Temperature
    kwargs["temperature"] = model_config.get(
        "temperature",
        DEFAULT_MODEL_CONFIG["temperature"],
    )

    # Max tokens
    kwargs["max_tokens"] = model_config.get(
        "max_tokens",
        DEFAULT_MODEL_CONFIG["max_tokens"],
    )

    # Model name
    kwargs["model"] = model_config.get(
        "model",
        DEFAULT_MODEL_CONFIG["model"],
    )

    # Timeout
    timeout = model_config.get("timeout", DEFAULT_MODEL_CONFIG["timeout"])
    kwargs["timeout"] = timeout
    kwargs["request_timeout"] = timeout

    return kwargs


def create_llm_client(
    config: Dict[str, Any],
    api_key: Optional[str] = None,
) -> Any:
    """Create a LangChain LLM client based on configuration.

    Args:
        config: Configuration dictionary with provider and model info.
        api_key: Optional API key (defaults to environment variable).

    Returns:
        Configured LangChain chat model.

    Raises:
        ValueError: If provider is not supported.
    """
    provider = config.get("provider", "openai").lower()
    model_kwargs = build_model_kwargs(config)

    if provider == "openai":
        return _create_openai_client(model_kwargs, api_key)
    elif provider == "azure":
        return _create_azure_client(config, model_kwargs, api_key)
    elif provider == "anthropic":
        return _create_anthropic_client(model_kwargs, api_key)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _create_openai_client(
    model_kwargs: Dict[str, Any],
    api_key: Optional[str] = None,
) -> Any:
    """Create OpenAI chat model.

    Args:
        model_kwargs: Model configuration.
        api_key: Optional API key.

    Returns:
        ChatOpenAI instance.
    """
    from langchain_openai import ChatOpenAI

    key = api_key or os.getenv("OPENAI_API_KEY")

    return ChatOpenAI(
        api_key=key,
        **model_kwargs,
    )


def _create_azure_client(
    config: Dict[str, Any],
    model_kwargs: Dict[str, Any],
    api_key: Optional[str] = None,
) -> Any:
    """Create Azure OpenAI chat model.

    Args:
        config: Full configuration with Azure-specific settings.
        model_kwargs: Model configuration.
        api_key: Optional API key.

    Returns:
        AzureChatOpenAI instance.

    Raises:
        ValueError: If required Azure configuration is missing.
    """
    from langchain_openai import AzureChatOpenAI

    key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = config.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = config.get("deployment_name") or config.get("model")

    if not endpoint:
        raise ValueError(
            "Azure endpoint must be provided via config.azure_endpoint or AZURE_OPENAI_ENDPOINT"
        )
    if not deployment:
        raise ValueError("Azure deployment name must be provided via config")

    return AzureChatOpenAI(
        api_key=key,
        azure_endpoint=endpoint,
        deployment_name=deployment,
        api_version=config.get("api_version", "2024-02-15-preview"),
        **{k: v for k, v in model_kwargs.items() if k != "model"},
    )


def _create_anthropic_client(
    model_kwargs: Dict[str, Any],
    api_key: Optional[str] = None,
) -> Any:
    """Create Anthropic chat model.

    Args:
        model_kwargs: Model configuration.
        api_key: Optional API key.

    Returns:
        ChatAnthropic instance.
    """
    from langchain_anthropic import ChatAnthropic

    key = api_key or os.getenv("ANTHROPIC_API_KEY")

    # Map model name if needed
    model = model_kwargs.get("model", "claude-3-opus-20240229")
    if model.startswith("gpt"):
        raise ValueError(
            f"Invalid model '{model}' for Anthropic provider. "
            "Use a Claude model name (e.g., 'claude-3-opus-20240229')"
        )

    return ChatAnthropic(
        api_key=key,
        model=model,
        temperature=model_kwargs.get("temperature", 0.0),
        max_tokens=model_kwargs.get("max_tokens", 4096),
    )


def get_supported_providers() -> list:
    """Get list of supported LLM providers.

    Returns:
        List of provider names.
    """
    return ["openai", "azure", "anthropic"]
