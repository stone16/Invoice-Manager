"""Settings and configuration API endpoints."""

import os
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.config import get_settings, clear_settings_cache
from app.services.llm_service import get_llm_service, reset_llm_service, PROVIDERS

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
    """Configure an LLM provider by setting environment variables.

    Note: This sets environment variables for the current process.
    For persistence, add these to your .env file.
    """
    provider = request.provider.lower()

    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的LLM提供商: {provider}。支持的提供商: {', '.join(PROVIDERS.keys())}"
        )

    if not request.api_key:
        raise HTTPException(status_code=400, detail="API密钥不能为空")

    try:
        # Set environment variables based on provider
        if provider == "openai":
            os.environ["OPENAI_API_KEY"] = request.api_key
            if request.model:
                os.environ["OPENAI_MODEL"] = request.model
            if request.base_url:
                os.environ["OPENAI_BASE_URL"] = request.base_url

        elif provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = request.api_key
            if request.model:
                os.environ["ANTHROPIC_MODEL"] = request.model

        elif provider == "google":
            os.environ["GOOGLE_API_KEY"] = request.api_key
            if request.model:
                os.environ["GOOGLE_MODEL"] = request.model

        elif provider == "qwen":
            os.environ["QWEN_API_KEY"] = request.api_key
            if request.model:
                os.environ["QWEN_MODEL"] = request.model
            if request.base_url:
                os.environ["QWEN_BASE_URL"] = request.base_url

        elif provider == "deepseek":
            os.environ["DEEPSEEK_API_KEY"] = request.api_key
            if request.model:
                os.environ["DEEPSEEK_MODEL"] = request.model
            if request.base_url:
                os.environ["DEEPSEEK_BASE_URL"] = request.base_url

        elif provider == "zhipu":
            os.environ["ZHIPU_API_KEY"] = request.api_key
            if request.model:
                os.environ["ZHIPU_MODEL"] = request.model

        # Set this as the active provider
        os.environ["LLM_PROVIDER"] = provider

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
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)}")


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
        raise HTTPException(
            status_code=500,
            detail=f"LLM连接测试失败: {str(e)}"
        )


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
