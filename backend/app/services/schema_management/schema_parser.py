from __future__ import annotations

from typing import Any, Dict

import yaml


def parse_yaml_schema(yaml_text: str) -> Dict[str, Any]:
    parsed = yaml.safe_load(yaml_text)
    if not isinstance(parsed, dict):
        raise ValueError("YAML schema must be a mapping")
    return parsed
