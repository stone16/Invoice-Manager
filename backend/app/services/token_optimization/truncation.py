"""Weighted page truncation with XML tag preservation."""

from __future__ import annotations

from typing import List

from app.services.token_optimization.encoder import get_encoder


def is_xml_tag(line: str) -> bool:
    """Check if line is an XML tag.

    Args:
        line: Line to check.

    Returns:
        True if line is an XML tag.
    """
    stripped = line.strip()
    if len(stripped) <= 2:
        return False
    return stripped.startswith("<") and stripped.endswith(">") and len(stripped) > 2


def calculate_page_weights(
    num_pages: int,
    decay_factor: float = 1.0,
) -> List[float]:
    """Calculate weights for pages, prioritizing earlier pages.

    Weight formula: weight[i] = 1.0 / ((i + 1) ** decay_factor)
    - Page 1: 1.0
    - Page 2: 0.5 (with decay_factor=1.0)
    - Page 3: 0.33

    Args:
        num_pages: Number of pages.
        decay_factor: Controls how quickly weight decreases.

    Returns:
        Normalized weights that sum to 1.0.
    """
    if num_pages == 0:
        return []

    weights = [1.0 / ((i + 1) ** decay_factor) for i in range(num_pages)]
    total_weight = sum(weights)
    return [w / total_weight for w in weights]


def allocate_tokens(
    page_token_counts: List[int],
    max_tokens: int,
    decay_factor: float = 1.0,
) -> List[int]:
    """Allocate tokens to pages based on weights.

    Args:
        page_token_counts: Token count for each page.
        max_tokens: Maximum total tokens allowed.
        decay_factor: Weight decay factor.

    Returns:
        Token allocation for each page.
    """
    n = len(page_token_counts)
    if n == 0:
        return []

    weights = calculate_page_weights(n, decay_factor)
    allocated = [int(w * max_tokens) for w in weights]

    # Handle rounding excess
    total_allocated = sum(allocated)
    if total_allocated > max_tokens:
        diff = total_allocated - max_tokens
        for i in range(n - 1, -1, -1):
            if diff <= 0:
                break
            reduction = min(diff, allocated[i])
            allocated[i] -= reduction
            diff -= reduction

    # Cap allocations at actual page token counts
    for i in range(n):
        if allocated[i] > page_token_counts[i]:
            allocated[i] = page_token_counts[i]

    return allocated


def truncate_with_tags(
    page_lines: List[str],
    max_tokens: int,
) -> str:
    """Truncate page content while preserving XML tags.

    Algorithm:
    1. Identify opening and closing tags
    2. Reserve tokens for tags
    3. Truncate content to fit remaining token budget
    4. Reconstruct with tags intact

    Args:
        page_lines: Lines of the page.
        max_tokens: Maximum tokens for this page.

    Returns:
        Truncated page text.
    """
    enc = get_encoder()

    if not page_lines:
        return ""

    # Join all lines for encoding
    full_text = "\n".join(page_lines)
    tokens = enc.encode(full_text)

    # If fits, return as-is
    if len(tokens) <= max_tokens:
        return full_text

    # Check for XML tags
    first_line = page_lines[0]
    last_line = page_lines[-1] if len(page_lines) > 1 else ""
    has_opening_tag = is_xml_tag(first_line)
    has_closing_tag = len(page_lines) > 1 and is_xml_tag(last_line)

    if not (has_opening_tag and has_closing_tag):
        # No tags to preserve, simple truncation
        truncated_tokens = tokens[:max_tokens]
        return enc.decode(truncated_tokens)

    opening_tag = first_line
    closing_tag = last_line
    content_lines = page_lines[1:-1] if len(page_lines) > 2 else []

    # Calculate token budget for tags
    opening_tokens = enc.encode(opening_tag)
    closing_tokens = enc.encode(closing_tag)
    newline_token = enc.encode("\n")
    tag_tokens = len(opening_tokens) + len(closing_tokens) + len(newline_token)
    if content_lines:
        tag_tokens += len(newline_token)

    if max_tokens <= tag_tokens:
        return opening_tag

    # Truncate content to fit
    content_max_tokens = max_tokens - tag_tokens
    content = "\n".join(content_lines)
    content_tokens = enc.encode(content)

    if len(content_tokens) <= content_max_tokens:
        return "\n".join(page_lines)

    truncated_content_tokens = content_tokens[:content_max_tokens]
    truncated_content = enc.decode(truncated_content_tokens)

    return f"{opening_tag}\n{truncated_content}\n{closing_tag}"


def apply_weighted_truncation(
    pages: List[List[str]],
    max_tokens: int,
    decay_factor: float = 1.0,
) -> List[str]:
    """Apply weighted truncation to pages, prioritizing earlier pages.

    Args:
        pages: List of pages, each page is list of lines.
        max_tokens: Maximum total tokens allowed.
        decay_factor: Controls how quickly weight decreases.

    Returns:
        List of truncated page strings.
    """
    enc = get_encoder()
    n = len(pages)
    if n == 0:
        return []

    # Encode all pages
    page_texts = ["\n".join(p) for p in pages]
    encoded_tokens = [enc.encode(text) for text in page_texts]
    token_counts = [len(tokens) for tokens in encoded_tokens]

    # Allocate tokens
    allocations = allocate_tokens(token_counts, max_tokens, decay_factor)

    # Truncate each page
    truncated_texts: List[str] = []
    for page_lines, allocation in zip(pages, allocations, strict=True):
        if allocation <= 0:
            continue
        truncated = truncate_with_tags(page_lines, allocation)
        if truncated:
            truncated_texts.append(truncated)

    return truncated_texts
