from __future__ import annotations

import re
from typing import Tuple

_CJK_PATTERN = re.compile(r"([\u4e00-\u9fff])\s+([\u4e00-\u9fff])")


def normalize_chinese_text(text: str) -> str:
    """Normalize spacing in Chinese text by removing CJK gaps."""
    if not text:
        return ""
    normalized = " ".join(text.split())
    while True:
        updated = _CJK_PATTERN.sub(r"\1\2", normalized)
        if updated == normalized:
            break
        normalized = updated
    return normalized


def normalize_text(text: str) -> Tuple[bool, str]:
    """Normalize text and return validity with processed result."""
    if not text:
        return False, ""
    stripped = text.strip()
    if not stripped:
        return False, ""
    return True, normalize_chinese_text(stripped)
