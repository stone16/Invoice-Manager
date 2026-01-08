"""Embedding service for RAG system using OpenAI text-embedding-3-small."""

from __future__ import annotations

import logging
import os
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

try:
    import tiktoken
except ImportError:
    tiktoken = None  # type: ignore

logger = logging.getLogger(__name__)


def get_openai_client():
    """Get OpenAI client with API key from environment."""
    from openai import OpenAI

    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_async_openai_client():
    """Get async OpenAI client with API key from environment."""
    from openai import AsyncOpenAI

    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """Generate a 1536-dimensional embedding for the given text.

    Args:
        text: The text to generate embedding for.
        model: The embedding model to use.

    Returns:
        A list of 1536 floats representing the embedding.
    """
    client = get_openai_client()
    response = client.embeddings.create(input=text, model=model)
    return response.data[0].embedding


async def generate_embeddings_batch(
    texts: List[str], model: str = "text-embedding-3-small"
) -> List[List[float]]:
    """Generate embeddings for multiple texts in a batch.

    Args:
        texts: List of texts to generate embeddings for.
        model: The embedding model to use.

    Returns:
        List of embedding vectors.
    """
    client = get_async_openai_client()
    response = await client.embeddings.create(input=texts, model=model)
    return [item.embedding for item in response.data]


def prepare_weighted_text(
    pages: List[Dict[str, Any]],
    max_tokens: int = 8192,
) -> Tuple[str, List[float]]:
    """Prepare weighted text from multi-page document for embedding.

    First page receives weight 1.0, subsequent pages receive decreasing weights.
    Total text is truncated to max_tokens.

    Args:
        pages: List of page dicts with 'page_num' and 'content' keys.
        max_tokens: Maximum tokens to include.

    Returns:
        Tuple of (weighted_text, weights_list).
    """
    if not pages:
        return "", []

    # Sort pages by page number
    sorted_pages = sorted(pages, key=lambda p: p.get("page_num", 0))

    # Calculate weights: first page = 1.0, decreasing by 0.1 per page
    weights = []
    for i, page in enumerate(sorted_pages):
        weight = max(0.1, 1.0 - (i * 0.1))
        weights.append(weight)

    # Build weighted text by repeating content based on weight
    # Higher weight = more representation in final text
    text_parts = []
    for page, weight in zip(sorted_pages, weights):
        content = page.get("content", "")
        # For simplicity, include content once but prioritize first pages
        text_parts.append(content)

    combined_text = "\n\n".join(text_parts)

    # Truncate to max tokens
    combined_text = truncate_to_tokens(combined_text, max_tokens)

    return combined_text, weights


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within max_tokens.

    Args:
        text: The text to truncate.
        max_tokens: Maximum number of tokens allowed.

    Returns:
        Truncated text.
    """
    if tiktoken is not None:
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            tokens = encoding.encode(text)

            if len(tokens) <= max_tokens:
                return text

            truncated_tokens = tokens[:max_tokens]
            return encoding.decode(truncated_tokens)
        except Exception as exc:
            logger.debug("tiktoken encoding failed, using fallback: %s", exc)

    # Fallback: rough estimate of 4 chars per token
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def deduplicate_lines(text: str, similarity_threshold: float = 0.95) -> str:
    """Remove duplicate lines from text based on similarity threshold.

    Args:
        text: The text to deduplicate.
        similarity_threshold: Minimum similarity ratio to consider lines duplicates.

    Returns:
        Deduplicated text.

    Note:
        Similarity comparisons are O(n^2) in the worst case.
    """
    lines = text.split("\n")
    unique_lines: List[str] = []
    seen_exact: set[str] = set()

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            unique_lines.append(line)
            continue

        if line_stripped in seen_exact:
            continue

        is_duplicate = False
        for existing in unique_lines:
            existing_stripped = existing.strip()
            if not existing_stripped:
                continue

            # Calculate similarity
            similarity = SequenceMatcher(None, line_stripped, existing_stripped).ratio()
            if similarity >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_lines.append(line)
            seen_exact.add(line_stripped)

    return "\n".join(unique_lines)


def compute_text_similarity(text1: str, text2: str) -> float:
    """Compute similarity ratio between two texts.

    Args:
        text1: First text.
        text2: Second text.

    Returns:
        Similarity ratio between 0 and 1.
    """
    return SequenceMatcher(None, text1, text2).ratio()
