"""Structured output parsing for LLM extraction results."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union


def parse_extraction_result(
    raw_output: Union[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Parse extraction result from LLM output.

    Handles both string JSON and pre-parsed dictionaries.
    Normalizes the structure to ensure consistent format.

    Args:
        raw_output: Raw output from LLM (string or dict).

    Returns:
        Parsed and normalized extraction result.

    Raises:
        ValueError: If the output cannot be parsed.
        TypeError: If the parsed output is not a dict.
    """
    # If string, parse as JSON
    if isinstance(raw_output, str):
        try:
            # Try to extract JSON from potential markdown code blocks
            cleaned = extract_json_from_text(raw_output)
            result = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON output: {e}") from e
    else:
        result = raw_output

    # Validate structure
    if not isinstance(result, dict):
        raise TypeError(f"Expected dict output, got {type(result).__name__}")

    # Normalize the result structure
    return normalize_result(result)


def extract_json_from_text(text: str) -> str:
    """Extract JSON from text that may contain markdown code blocks.

    Args:
        text: Text potentially containing JSON in code blocks.

    Returns:
        Extracted JSON string.
    """
    text = text.strip()

    # Check for markdown code blocks
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()

    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()

    # Try to find JSON object boundaries
    if "{" in text:
        start = text.find("{")
        # Find matching closing brace
        depth = 0
        for i, char in enumerate(text[start:], start):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

    return text


def normalize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize extraction result to consistent structure.

    Ensures all fields have the expected {value, data_source} format.

    Args:
        result: Raw extraction result.

    Returns:
        Normalized result with consistent structure.
    """
    normalized = {}

    for key, value in result.items():
        normalized[key] = normalize_field(value)

    return normalized


def normalize_field(value: Any) -> Any:
    """Normalize a single field value.

    Args:
        value: Field value to normalize.

    Returns:
        Normalized field value.
    """
    if isinstance(value, dict):
        # Already has value/data_source structure
        if "value" in value:
            return {
                "value": normalize_value(value["value"]),
                "data_source": value.get("data_source", {}),
                **{
                    k: v
                    for k, v in value.items()
                    if k not in ("value", "data_source")
                },
            }
        # Nested object without value/data_source
        return {k: normalize_field(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [normalize_field(item) for item in value]

    # Primitive value
    return value


def normalize_value(value: Any) -> Any:
    """Normalize the value part of a field.

    Args:
        value: Value to normalize.

    Returns:
        Normalized value.
    """
    if isinstance(value, dict):
        # Nested object value
        return {k: normalize_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [normalize_value(item) for item in value]
    return value


def build_extraction_response(
    extracted_data: Dict[str, Any],
    status: str = "success",
    errors: Optional[List[str]] = None,
    raw_response: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a standardized extraction response.

    Args:
        extracted_data: The extracted data.
        status: Status of the extraction ("success", "error", "review_required").
        errors: List of error messages if any.
        raw_response: Raw LLM response for debugging.
        trace_id: LangSmith trace ID if available.

    Returns:
        Standardized response dictionary.
    """
    response = {
        "status": status,
        "data": extracted_data,
    }

    if errors:
        response["errors"] = errors

    if raw_response is not None:
        response["raw_response"] = raw_response

    if trace_id:
        response["trace_id"] = trace_id

    return response
