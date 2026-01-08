from __future__ import annotations

from typing import List


def next_schema_version(versions: List[int]) -> int:
    """Calculate the next schema version number.

    Args:
        versions: List of existing version numbers

    Returns:
        Next version number (max + 1, or 1 if empty)
    """
    if not versions:
        return 1
    return max(versions) + 1
