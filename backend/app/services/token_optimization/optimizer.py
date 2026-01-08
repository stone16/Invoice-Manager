"""High-level token optimization functions."""

from __future__ import annotations

from typing import Any, Dict, List

from app.services.token_optimization.deduplication import remove_duplicated_lines
from app.services.token_optimization.encoder import count_tokens, get_encoder
from app.services.token_optimization.truncation import apply_weighted_truncation


def optimize_for_embedding(
    text_blocks: List[Dict[str, Any]],
    max_tokens: int = 8192,
    deduplicate: bool = True,
) -> str:
    """Optimize text blocks for embedding generation.

    Args:
        text_blocks: List of text blocks with 'page' and 'lines' keys.
        max_tokens: Maximum tokens for embedding.
        deduplicate: Whether to deduplicate lines.

    Returns:
        Optimized text for embedding.
    """
    # Extract lines from blocks
    pages = [block.get("lines", []) for block in text_blocks]

    if deduplicate:
        pages = remove_duplicated_lines(pages)

    # Apply weighted truncation
    truncated_pages = apply_weighted_truncation(pages, max_tokens)

    return "\n\n".join(truncated_pages)


def optimize_for_prompt(
    pages: List[List[str]],
    max_tokens: int = 8192,
    deduplicate: bool = True,
    decay_factor: float = 1.0,
) -> str:
    """Optimize pages for LLM prompt.

    Args:
        pages: List of pages, each page is list of lines.
        max_tokens: Maximum tokens for prompt.
        deduplicate: Whether to deduplicate lines.
        decay_factor: Weight decay for page prioritization.

    Returns:
        Optimized text for LLM prompt.
    """
    if deduplicate:
        pages = remove_duplicated_lines(pages)

    truncated_pages = apply_weighted_truncation(
        pages, max_tokens, decay_factor=decay_factor
    )

    return "\n\n".join(truncated_pages)


def build_weighted_embedding_text(
    labeled_texts: List[Dict[str, str]],
    max_tokens: int = 8192,
    decay_factor: float = 1.0,
) -> str:
    """Build weighted embedding text from labeled text segments.

    Args:
        labeled_texts: List of dicts with 'label' and 'text' keys.
        max_tokens: Maximum tokens allowed.
        decay_factor: Weight decay for segment prioritization.

    Returns:
        Combined and weighted text for embedding.
    """
    enc = get_encoder()

    if not labeled_texts:
        return ""

    n = len(labeled_texts)

    # Calculate weights
    weights = [1.0 / ((i + 1) ** decay_factor) for i in range(n)]
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    # Allocate tokens
    allocations = [int(w * max_tokens) for w in normalized_weights]

    # Build result
    result_parts: List[str] = []
    for item, allocation in zip(labeled_texts, allocations):
        text = item.get("text", "")
        label = item.get("label", "")

        if not text:
            continue

        tokens = enc.encode(text)
        if len(tokens) <= allocation:
            result_parts.append(f"[{label}]\n{text}" if label else text)
        else:
            # Truncate to fit
            truncated_tokens = tokens[:allocation]
            truncated_text = enc.decode(truncated_tokens)
            result_parts.append(f"[{label}]\n{truncated_text}" if label else truncated_text)

    return "\n\n".join(result_parts)


def estimate_token_savings(
    original_text: str,
    optimized_text: str,
) -> Dict[str, Any]:
    """Estimate token savings from optimization.

    Args:
        original_text: Original text before optimization.
        optimized_text: Optimized text after processing.

    Returns:
        Dict with token counts and savings percentage.
    """
    original_tokens = count_tokens(original_text)
    optimized_tokens = count_tokens(optimized_text)

    savings = original_tokens - optimized_tokens
    savings_pct = (savings / original_tokens * 100) if original_tokens > 0 else 0.0

    return {
        "original_tokens": original_tokens,
        "optimized_tokens": optimized_tokens,
        "tokens_saved": savings,
        "savings_percentage": round(savings_pct, 2),
    }
