"""Settings and configuration API endpoints."""

import logging
import os
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)


def _update_env_file(updates: dict[str, str]) -> None:
    """Update .env file with new key-value pairs.

    Preserves existing entries and comments, updates existing keys,
    and appends new keys at the end.
    """
    env_path = Path(__file__).parent.parent.parent / ".env"

    # Read existing content
    existing_lines = []
    existing_keys = set()
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                stripped = line.strip()
                # Track existing keys (ignore comments and empty lines)
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                    existing_keys.add(key)
                existing_lines.append(line)

    # Update existing lines or mark keys as handled
    updated_keys = set()
    new_lines = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                # Replace this line with updated value
                new_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Append new keys that weren't in the file
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")

    # Write back
    with open(env_path, "w") as f:
        f.writelines(new_lines)

    logger.info(f"Updated .env file with keys: {list(updates.keys())}")

from app.config import get_settings, clear_settings_cache
from app.services.llm_service import get_llm_service, reset_llm_service, PROVIDERS
from app.services.model_registry import get_models_with_fallback

router = APIRouter()


class LLMProviderInfo(BaseModel):
    """Information about an LLM provider."""
    name: str
    display_name: str
    is_configured: bool
    model: Optional[str] = None


class LLMStatusResponse(BaseModel):
    """Response for LLM status check."""
    is_configured: bool
    active_provider: Optional[str] = None
    active_provider_display: Optional[str] = None
    configured_providers: List[str] = []
    available_providers: List[LLMProviderInfo] = []


class LLMConfigRequest(BaseModel):
    """Request to configure an LLM provider."""
    provider: str
    api_key: str
    model: Optional[str] = None
    base_url: Optional[str] = None


class LLMConfigResponse(BaseModel):
    """Response after configuring LLM."""
    success: bool
    message: str
    provider: Optional[str] = None


# Display names for providers
PROVIDER_DISPLAY_NAMES = {
    "openai": "OpenAI (GPT)",
    "anthropic": "Anthropic (Claude)",
    "google": "Google (Gemini)",
    "qwen": "阿里云 (通义千问)",
    "deepseek": "DeepSeek",
    "zhipu": "智谱 (GLM)",
}

# Default models for providers
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-haiku-20240307",
    "google": "gemini-1.5-flash",
    "qwen": "qwen-turbo",
    "deepseek": "deepseek-chat",
    "zhipu": "glm-4-flash",
}


@router.get("/llm/status", response_model=LLMStatusResponse)
async def get_llm_status():
    """Get LLM configuration status."""
    settings = get_settings()
    llm_service = get_llm_service()

    active_provider = settings.get_active_llm_provider()
    configured_providers = llm_service.get_configured_providers()

    # Build available providers list
    available_providers = []
    for name in PROVIDERS.keys():
        provider_info = LLMProviderInfo(
            name=name,
            display_name=PROVIDER_DISPLAY_NAMES.get(name, name),
            is_configured=name in configured_providers,
            model=_get_provider_model(name) if name in configured_providers else DEFAULT_MODELS.get(name),
        )
        available_providers.append(provider_info)

    return LLMStatusResponse(
        is_configured=settings.is_llm_configured(),
        active_provider=active_provider,
        active_provider_display=PROVIDER_DISPLAY_NAMES.get(active_provider, active_provider) if active_provider else None,
        configured_providers=configured_providers,
        available_providers=available_providers,
    )


@router.post("/llm/configure", response_model=LLMConfigResponse)
async def configure_llm(request: LLMConfigRequest):
    """Configure an LLM provider and persist to .env file."""
    provider = request.provider.lower()

    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的LLM提供商: {provider}。支持的提供商: {', '.join(PROVIDERS.keys())}"
        )

    if not request.api_key:
        raise HTTPException(status_code=400, detail="API密钥不能为空")

    try:
        # Build env updates for both os.environ and .env file
        env_updates: dict[str, str] = {"LLM_PROVIDER": provider}

        # Provider-specific configuration
        provider_config = {
            "openai": ("OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL"),
            "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", None),
            "google": ("GOOGLE_API_KEY", "GOOGLE_MODEL", None),
            "qwen": ("QWEN_API_KEY", "QWEN_MODEL", "QWEN_BASE_URL"),
            "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "DEEPSEEK_BASE_URL"),
            "zhipu": ("ZHIPU_API_KEY", "ZHIPU_MODEL", None),
        }

        key_name, model_name, base_url_name = provider_config[provider]
        env_updates[key_name] = request.api_key
        if request.model:
            env_updates[model_name] = request.model
        if request.base_url and base_url_name:
            env_updates[base_url_name] = request.base_url

        # Set environment variables for current process
        for key, value in env_updates.items():
            os.environ[key] = value

        # Persist to .env file for restart persistence
        _update_env_file(env_updates)

        # Clear caches to reload settings
        clear_settings_cache()
        reset_llm_service()

        # Verify configuration
        new_settings = get_settings()
        if not new_settings.is_llm_configured():
            raise HTTPException(status_code=500, detail="配置失败，请检查API密钥是否正确")

        return LLMConfigResponse(
            success=True,
            message=f"已成功配置 {PROVIDER_DISPLAY_NAMES.get(provider, provider)}",
            provider=provider,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM configuration failed: {e}")
        raise HTTPException(status_code=500, detail="配置失败，请检查配置参数是否正确") from e


@router.post("/llm/test")
async def test_llm_connection():
    """Test the current LLM configuration with a simple request."""
    llm_service = get_llm_service()

    if not llm_service.is_available:
        raise HTTPException(status_code=400, detail="未配置LLM提供商")

    try:
        provider = llm_service.active_provider
        if not provider:
            raise HTTPException(status_code=500, detail="无法获取LLM提供商实例")

        # Simple test prompt
        response = provider.chat_completion(
            "You are a helpful assistant.",
            "Reply with exactly: OK"
        )

        return {
            "success": True,
            "provider": provider.get_provider_name(),
            "provider_display": PROVIDER_DISPLAY_NAMES.get(provider.get_provider_name(), provider.get_provider_name()),
            "message": "LLM连接测试成功",
            "response": response[:100],  # Limit response length
        }

    except Exception as e:
        logger.error(f"LLM connection test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="LLM连接测试失败，请检查API密钥和网络连接"
        ) from e


def _get_provider_model(provider_name: str) -> Optional[str]:
    """Get the configured model for a provider."""
    settings = get_settings()
    model_map = {
        "openai": settings.openai_model,
        "anthropic": settings.anthropic_model,
        "google": settings.google_model,
        "qwen": settings.qwen_model,
        "deepseek": settings.deepseek_model,
        "zhipu": settings.zhipu_model,
    }
    return model_map.get(provider_name)


class ModelInfo(BaseModel):
    """Information about a model."""
    id: str
    name: str
    vision: bool
    context_length: Optional[int] = None
    pricing: Optional[dict] = None


class ModelsResponse(BaseModel):
    """Response for available models."""
    models: List[ModelInfo]
    source: str  # "openrouter" or "fallback"


@router.get("/models", response_model=ModelsResponse)
async def get_available_models(
    provider: Optional[str] = None,
    vision_only: bool = False
):
    """Get available models, optionally filtered by provider or vision capability.

    Args:
        provider: Filter by provider name (openai, anthropic, google, qwen, deepseek, zhipu)
        vision_only: If true, only return models that support image input

    Returns:
        List of available models with their capabilities
    """
    if provider:
        if provider.lower() not in PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的LLM提供商: {provider}。支持的提供商: {', '.join(PROVIDERS.keys())}"
            )
        models = get_models_with_fallback(provider, vision_only)
    else:
        # Get models for all providers
        all_models = []
        for prov in PROVIDERS.keys():
            all_models.extend(get_models_with_fallback(prov, vision_only))
        models = all_models

    # Determine source based on model ID format (OpenRouter uses "provider/model" format)
    source = "openrouter" if models and "/" in models[0].get("id", "") else "fallback"

    return ModelsResponse(
        models=[ModelInfo(**m) for m in models],
        source=source
    )
