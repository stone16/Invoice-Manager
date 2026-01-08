"""Tiktoken encoder utilities with caching."""

from __future__ import annotations

from typing import List, Optional

import tiktoken

# Global encoder cache - initialize once, reuse everywhere
_ENCODER_CACHE: Optional[tiktoken.Encoding] = None
_ENCODER_MODEL = "cl100k_base"  # GPT-4, GPT-3.5-turbo compatible encoding


def get_encoder() -> tiktoken.Encoding:
    """Get cached tiktoken encoder.

    Initialize once, reuse everywhere for performance.

    Returns:
        Cached tiktoken encoder instance.
    """
    global _ENCODER_CACHE
    if _ENCODER_CACHE is None:
        _ENCODER_CACHE = tiktoken.get_encoding(_ENCODER_MODEL)
    return _ENCODER_CACHE


def count_tokens(text: str) -> int:
    """Count tokens in text.

    Args:
        text: Text to count tokens for.

    Returns:
        Number of tokens.
    """
    encoder = get_encoder()
    return len(encoder.encode(text))


def encode_text(text: str) -> List[int]:
    """Encode text to tokens.

    Args:
        text: Text to encode.

    Returns:
        List of token IDs.
    """
    encoder = get_encoder()
    return encoder.encode(text)


def decode_tokens(tokens: List[int]) -> str:
    """Decode tokens back to text.

    Args:
        tokens: List of token IDs.

    Returns:
        Decoded text.
    """
    encoder = get_encoder()
    return encoder.decode(tokens)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to max tokens.

    Args:
        text: Text to truncate.
        max_tokens: Maximum number of tokens.

    Returns:
        Truncated text.
    """
    encoder = get_encoder()
    tokens = encoder.encode(text)
    if len(tokens) <= max_tokens:
        return text
    truncated_tokens = tokens[:max_tokens]
    return encoder.decode(truncated_tokens)
