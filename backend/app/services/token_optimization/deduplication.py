"""Tiktoken-based line deduplication utilities."""

from __future__ import annotations

from typing import List, Set

from app.services.token_optimization.encoder import get_encoder

# Default similarity threshold for considering lines as duplicates
SIMILARITY_THRESHOLD = 0.95


def remove_duplicated_lines(
    page_lines_list: List[List[str]],
    similarity_threshold: float = SIMILARITY_THRESHOLD,
) -> List[List[str]]:
    """Remove duplicate lines across all pages using tiktoken-based similarity.

    Algorithm:
    1. Maintain a set of seen lines and their normalized forms
    2. For each line, check if it's an exact duplicate (normalized)
    3. If not exact, calculate tiktoken-based Jaccard similarity
    4. Skip lines that are >= similarity_threshold similar to any seen line

    Args:
        page_lines_list: List of pages, where each page is a list of lines.
        similarity_threshold: Minimum similarity to consider as duplicate.

    Returns:
        List of pages with duplicates removed.
    """
    seen_lines: List[str] = []
    seen_normalized: Set[str] = set()
    result: List[List[str]] = []

    for page_lines in page_lines_list:
        filtered_lines: List[str] = []
        for line in page_lines:
            # Preserve empty lines
            if not line.strip():
                filtered_lines.append(line)
                continue

            normalized = _normalize_line(line)

            # Check for exact duplicate
            if normalized in seen_normalized:
                continue

            # Check for similar duplicates
            is_duplicate = False
            for seen_line in seen_lines:
                similarity = calculate_line_similarity(line, seen_line)
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                filtered_lines.append(line)
                seen_lines.append(line)
                seen_normalized.add(normalized)

        result.append(filtered_lines)

    return result


def calculate_line_similarity(line1: str, line2: str) -> float:
    """Calculate tiktoken-based Jaccard similarity between two lines.

    IMPORTANT: Uses tiktoken tokens, NOT word tokens.

    Args:
        line1: First line.
        line2: Second line.

    Returns:
        Jaccard similarity between 0.0 and 1.0.
    """
    enc = get_encoder()

    if not line1.strip() or not line2.strip():
        if not line1.strip() and not line2.strip():
            return 1.0
        return 0.0

    normalized1 = _normalize_line(line1)
    normalized2 = _normalize_line(line2)

    # Exact match
    if normalized1 == normalized2:
        return 1.0

    # Convert to token sets using tiktoken
    tokens1 = set(enc.encode(normalized1))
    tokens2 = set(enc.encode(normalized2))

    if not tokens1 or not tokens2:
        return 0.0

    # Jaccard similarity: |A ∩ B| / |A ∪ B|
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)

    return intersection / union if union > 0 else 0.0


def _normalize_line(line: str) -> str:
    """Normalize line for comparison.

    Args:
        line: Line to normalize.

    Returns:
        Normalized line (lowercase, whitespace normalized).
    """
    return " ".join(line.lower().split())


def deduplicate_text(text: str, similarity_threshold: float = SIMILARITY_THRESHOLD) -> str:
    """Deduplicate lines in text.

    Args:
        text: Text with potential duplicate lines.
        similarity_threshold: Minimum similarity to consider as duplicate.

    Returns:
        Text with duplicate lines removed.
    """
    lines = text.split("\n")
    result_pages = remove_duplicated_lines([lines], similarity_threshold)
    return "\n".join(result_pages[0])
