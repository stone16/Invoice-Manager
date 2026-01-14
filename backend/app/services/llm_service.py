"""LLM-based invoice parsing service with multi-provider support."""

import base64
import json
import logging
import re
import threading
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from app.config import get_settings

# Thread lock for singleton initialization
_llm_lock = threading.Lock()
from app.services.prompts import (
    INVOICE_VISION_PROMPT,
    INVOICE_VISION_SYSTEM_PROMPT,
    REQUIRED_FIELDS,
)

logger = logging.getLogger(__name__)
settings = get_settings()


def _model_matches_vision_pattern(model_name: str, vision_patterns: list[str]) -> bool:
    """Check if a model name matches any vision pattern.

    Uses exact match or prefix match with separator to avoid false positives.
    For example, "gpt-4o" matches "gpt-4o" and "gpt-4o-mini" but not "gpt-4o-audio".

    Args:
        model_name: The configured model name
        vision_patterns: List of known vision model patterns

    Returns:
        True if the model supports vision
    """
    for pattern in vision_patterns:
        # Exact match
        if model_name == pattern:
            return True
        # Prefix match: pattern must be followed by a separator (-) or end
        if model_name.startswith(pattern + "-") or model_name.startswith(pattern + "."):
            return True
    return False


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is configured."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name."""
        pass

    @abstractmethod
    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        """Send chat completion request and return response content."""
        pass

    def supports_vision(self) -> bool:
        """Check if provider supports vision/image input."""
        return False

    def vision_completion(self, system_prompt: str, user_prompt: str, image_data: bytes, mime_type: str = "image/png") -> str:
        """Send vision completion request with image and return response content.

        Args:
            system_prompt: System prompt for the model
            user_prompt: User prompt/instructions
            image_data: Raw image bytes
            mime_type: MIME type of the image (image/png, image/jpeg, etc.)

        Returns:
            Response content from the model
        """
        raise NotImplementedError("Vision not supported by this provider")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI/OpenAI-compatible provider."""

    # Models that support vision
    VISION_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4-vision-preview"]

    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    @property
    def client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    from openai import OpenAI
                    kwargs = {"api_key": settings.openai_api_key}
                    if settings.openai_base_url:
                        kwargs["base_url"] = settings.openai_base_url
                    self._client = OpenAI(**kwargs)
        return self._client

    def is_configured(self) -> bool:
        return bool(settings.openai_api_key)

    def get_provider_name(self) -> str:
        return "openai"

    def supports_vision(self) -> bool:
        return _model_matches_vision_pattern(settings.openai_model, self.VISION_MODELS)

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()

    def vision_completion(self, system_prompt: str, user_prompt: str, image_data: bytes, mime_type: str = "image/png") -> str:
        base64_image = base64.b64encode(image_data).decode("utf-8")
        response = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""

    # All Claude 3 models support vision
    VISION_MODELS = ["claude-3", "claude-3.5"]

    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    @property
    def client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    import anthropic
                    self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def is_configured(self) -> bool:
        return bool(settings.anthropic_api_key)

    def get_provider_name(self) -> str:
        return "anthropic"

    def supports_vision(self) -> bool:
        return _model_matches_vision_pattern(settings.anthropic_model, self.VISION_MODELS)

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
        )
        return response.content[0].text.strip()

    def vision_completion(self, system_prompt: str, user_prompt: str, image_data: bytes, mime_type: str = "image/png") -> str:
        base64_image = base64.b64encode(image_data).decode("utf-8")
        response = self.client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1500,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": base64_image
                            }
                        },
                        {"type": "text", "text": user_prompt}
                    ]
                }
            ],
        )
        return response.content[0].text.strip()


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider."""

    # Gemini models with vision support
    VISION_MODELS = ["gemini-1.5", "gemini-2", "gemini-pro-vision"]

    def __init__(self):
        self._model = None
        self._genai = None
        self._lock = threading.Lock()

    @property
    def genai(self):
        if self._genai is None:
            with self._lock:
                if self._genai is None:
                    import google.generativeai as genai
                    genai.configure(api_key=settings.google_api_key)
                    self._genai = genai
        return self._genai

    @property
    def model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = self.genai.GenerativeModel(settings.google_model)
        return self._model

    def is_configured(self) -> bool:
        return bool(settings.google_api_key)

    def get_provider_name(self) -> str:
        return "google"

    def supports_vision(self) -> bool:
        return _model_matches_vision_pattern(settings.google_model, self.VISION_MODELS)

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        # Gemini combines system and user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = self.model.generate_content(full_prompt)
        return response.text.strip()

    def vision_completion(self, system_prompt: str, user_prompt: str, image_data: bytes, mime_type: str = "image/png") -> str:
        from PIL import Image
        from io import BytesIO

        # Convert bytes to PIL Image for Gemini
        image = Image.open(BytesIO(image_data))

        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        response = self.model.generate_content([full_prompt, image])
        return response.text.strip()


class QwenProvider(BaseLLMProvider):
    """Alibaba Qwen provider (OpenAI-compatible)."""

    # Qwen-VL models support vision
    VISION_MODELS = ["qwen-vl", "qwen2-vl"]

    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    @property
    def client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    from openai import OpenAI
                    self._client = OpenAI(
                        api_key=settings.qwen_api_key,
                        base_url=settings.qwen_base_url,
                    )
        return self._client

    def is_configured(self) -> bool:
        return bool(settings.qwen_api_key)

    def get_provider_name(self) -> str:
        return "qwen"

    def supports_vision(self) -> bool:
        return _model_matches_vision_pattern(settings.qwen_model, self.VISION_MODELS)

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=settings.qwen_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()

    def vision_completion(self, system_prompt: str, user_prompt: str, image_data: bytes, mime_type: str = "image/png") -> str:
        base64_image = base64.b64encode(image_data).decode("utf-8")
        response = self.client.chat.completions.create(
            model=settings.qwen_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek provider (OpenAI-compatible)."""

    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    @property
    def client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    from openai import OpenAI
                    self._client = OpenAI(
                        api_key=settings.deepseek_api_key,
                        base_url=settings.deepseek_base_url,
                    )
        return self._client

    def is_configured(self) -> bool:
        return bool(settings.deepseek_api_key)

    def get_provider_name(self) -> str:
        return "deepseek"

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()


class ZhipuProvider(BaseLLMProvider):
    """Zhipu GLM provider."""

    # GLM-4V models support vision
    VISION_MODELS = ["glm-4v"]

    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    @property
    def client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    from zhipuai import ZhipuAI
                    self._client = ZhipuAI(api_key=settings.zhipu_api_key)
        return self._client

    def is_configured(self) -> bool:
        return bool(settings.zhipu_api_key)

    def get_provider_name(self) -> str:
        return "zhipu"

    def supports_vision(self) -> bool:
        return _model_matches_vision_pattern(settings.zhipu_model, self.VISION_MODELS)

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=settings.zhipu_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()

    def vision_completion(self, system_prompt: str, user_prompt: str, image_data: bytes, mime_type: str = "image/png") -> str:
        base64_image = base64.b64encode(image_data).decode("utf-8")
        response = self.client.chat.completions.create(
            model=settings.zhipu_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{system_prompt}\n\n{user_prompt}"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()


# Provider registry
PROVIDERS: Dict[str, type] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "qwen": QwenProvider,
    "deepseek": DeepSeekProvider,
    "zhipu": ZhipuProvider,
}


class LLMService:
    """Handles LLM-based invoice parsing with multi-provider support."""

    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._active_provider: Optional[BaseLLMProvider] = None

    def _get_provider(self, provider_name: str) -> Optional[BaseLLMProvider]:
        """Get or create a provider instance."""
        if provider_name not in self._providers:
            if provider_name in PROVIDERS:
                self._providers[provider_name] = PROVIDERS[provider_name]()
        return self._providers.get(provider_name)

    @property
    def active_provider(self) -> Optional[BaseLLMProvider]:
        """Get the active LLM provider."""
        if self._active_provider is None:
            provider_name = settings.get_active_llm_provider()
            if provider_name:
                self._active_provider = self._get_provider(provider_name)
        return self._active_provider

    @property
    def is_available(self) -> bool:
        """Check if any LLM provider is available."""
        return settings.is_llm_configured()

    def get_configured_providers(self) -> list[str]:
        """Get list of configured provider names."""
        configured = []
        for name, provider_class in PROVIDERS.items():
            provider = self._get_provider(name)
            if provider and provider.is_configured():
                configured.append(name)
        return configured

    def get_active_provider_name(self) -> Optional[str]:
        """Get the name of the active provider."""
        return settings.get_active_llm_provider()

    def supports_vision(self) -> bool:
        """Check if the active provider supports vision/image input."""
        provider = self.active_provider
        return provider.supports_vision() if provider else False

    def parse_invoice_from_image(self, image_data: bytes, mime_type: str = "image/png") -> Dict[str, Any]:
        """Parse invoice directly from image using vision capabilities.

        Args:
            image_data: Raw image bytes
            mime_type: MIME type of the image

        Returns:
            Dictionary of extracted fields
        """
        if not self.is_available:
            logger.warning("No LLM provider configured, skipping vision parsing")
            return {}

        provider = self.active_provider
        if not provider:
            logger.warning("Failed to get active LLM provider")
            return {}

        if not provider.supports_vision():
            logger.warning(f"Provider {provider.get_provider_name()} does not support vision")
            return {}

        try:
            content = provider.vision_completion(
                INVOICE_VISION_SYSTEM_PROMPT,
                INVOICE_VISION_PROMPT,
                image_data,
                mime_type
            )

            return self._parse_json_response(content, provider.get_provider_name())

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM vision response as JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"LLM vision parsing failed ({provider.get_provider_name()}): {e}")
            return {}

    def _normalize_field_value(self, field_name: str, value: Any) -> Optional[str]:
        """Normalize and validate a single field value."""
        if value is None:
            return None

        if isinstance(value, (int, float)):
            value = str(value)
        if not isinstance(value, str):
            return None

        cleaned = value.strip()
        if not cleaned:
            return None

        if field_name in ['total_with_tax', 'amount', 'tax_amount']:
            cleaned = re.sub(r'[¥￥$€,，\s]', '', cleaned)
            match = re.search(r'(\d+(?:\.\d{1,2})?)', cleaned)
            return match.group(1) if match else None

        if field_name == 'issue_date':
            match = re.search(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})', cleaned)
            if match:
                year, month, day = match.groups()
                return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}', cleaned):
                return cleaned
            return None

        if field_name == 'invoice_number':
            cleaned = re.sub(r'[\s-]+', '', cleaned)
            return cleaned if re.fullmatch(r'\d{8,20}', cleaned) else None

        if field_name == 'invoice_code':
            cleaned = re.sub(r'[\s-]+', '', cleaned)
            return cleaned if re.fullmatch(r'\d{10,12}', cleaned) else None

        if field_name in ['buyer_tax_id', 'seller_tax_id']:
            cleaned = re.sub(r'\s+', '', cleaned.upper())
            return cleaned if re.fullmatch(r'[A-Z0-9]{15,20}', cleaned) else None

        if field_name == 'tax_rate':
            if cleaned == '免税':
                return cleaned
            return cleaned if re.fullmatch(r'\d+%', cleaned) else None

        return cleaned

    def _parse_json_response(self, content: str, provider_name: str) -> Dict[str, Any]:
        """Parse JSON from LLM response with schema validation and data cleaning.

        Args:
            content: Raw response content from LLM
            provider_name: Name of the provider for logging

        Returns:
            Parsed and validated dictionary of fields
        """
        # Try to extract JSON from response
        if content.startswith("```"):
            # Remove markdown code blocks
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        raw_fields = json.loads(content)
        if not isinstance(raw_fields, dict):
            raise json.JSONDecodeError("LLM response is not a JSON object", content, 0)

        fields: Dict[str, Optional[str]] = {}
        for field in REQUIRED_FIELDS:
            fields[field] = self._normalize_field_value(field, raw_fields.get(field))

        logger.info(f"LLM ({provider_name}) extracted fields: {list(fields.keys())}")
        return fields


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get thread-safe LLMService singleton."""
    global _llm_service
    if _llm_service is None:
        with _llm_lock:
            # Double-check after acquiring lock
            if _llm_service is None:
                _llm_service = LLMService()
    return _llm_service


def reset_llm_service():
    """Reset the LLM service singleton (useful after config changes)."""
    global _llm_service
    with _llm_lock:
        _llm_service = None
