"""Validation utilities for LLM extraction results."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set


# PDF Block ID pattern: page.section.block:line:char or similar
PDF_BLOCK_ID_PATTERN = re.compile(r"^\d+\.\d+\.\d+:\d+:\d+$")

# Excel Block ID patterns: sheet.row.cell or sheet.row.range
EXCEL_BLOCK_ID_PATTERN = re.compile(r"^\d+\.\d+\.[A-Z]+\d*(?::[A-Z]+\d*)?$")


def validate_block_id(block_id: str, document_type: str = "pdf") -> bool:
    """Validate a Block ID format based on document type.

    Args:
        block_id: The Block ID to validate.
        document_type: Type of document ("pdf" or "excel").

    Returns:
        True if the Block ID format is valid, False otherwise.
    """
    if not block_id or not isinstance(block_id, str):
        return False

    if document_type == "pdf":
        return bool(PDF_BLOCK_ID_PATTERN.match(block_id))
    elif document_type == "excel":
        return bool(EXCEL_BLOCK_ID_PATTERN.match(block_id))
    else:
        # Default to PDF validation
        return bool(PDF_BLOCK_ID_PATTERN.match(block_id))


def extract_block_ids_from_result(
    result: Dict[str, Any],
    block_ids: Optional[Set[str]] = None,
) -> Set[str]:
    """Extract all Block IDs from an extraction result.

    Args:
        result: Extraction result dictionary.
        block_ids: Optional set to accumulate block IDs into.

    Returns:
        Set of all Block IDs found in the result.
    """
    if block_ids is None:
        block_ids = set()

    if isinstance(result, dict):
        # Check for data_source with block_id
        if "data_source" in result and isinstance(result["data_source"], dict):
            bid = result["data_source"].get("block_id")
            if bid:
                block_ids.add(bid)

        # Recurse into nested dicts
        for key, value in result.items():
            if isinstance(value, dict):
                extract_block_ids_from_result(value, block_ids)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        extract_block_ids_from_result(item, block_ids)

    return block_ids


def validate_extraction_result(
    result: Dict[str, Any],
    available_block_ids: Set[str],
    document_type: str = "pdf",
) -> List[str]:
    """Validate extraction result Block IDs against available IDs.

    Args:
        result: Extraction result dictionary.
        available_block_ids: Set of valid Block IDs from the document.
        document_type: Type of document for format validation.

    Returns:
        List of error messages. Empty list if all valid.
    """
    errors = []

    # Extract all block IDs referenced in the result
    referenced_block_ids = extract_block_ids_from_result(result)

    for block_id in referenced_block_ids:
        # Check format validity
        if not validate_block_id(block_id, document_type):
            errors.append(f"Invalid Block ID format: {block_id}")
            continue

        # Check if block ID exists in document
        if block_id not in available_block_ids:
            errors.append(f"Block ID not found in document: {block_id}")

    return errors


def validate_required_fields(
    result: Dict[str, Any],
    schema: Dict[str, Any],
) -> List[str]:
    """Validate that required fields are present in the result.

    Args:
        result: Extraction result dictionary.
        schema: JSON schema with required fields.

    Returns:
        List of error messages for missing required fields.
    """
    errors = []
    required = schema.get("required", [])

    for field in required:
        if field not in result:
            errors.append(f"Missing required field: {field}")
        elif result[field] is None:
            errors.append(f"Required field is null: {field}")
        elif isinstance(result[field], dict):
            # Check if value is present
            if result[field].get("value") is None:
                errors.append(f"Required field has no value: {field}")

    return errors


def validate_data_source_completeness(
    result: Dict[str, Any],
) -> List[str]:
    """Validate that all fields with values have data_source.

    Args:
        result: Extraction result dictionary.

    Returns:
        List of error messages for fields missing data_source.
    """
    errors = []

    def check_field(field_name: str, field_value: Any) -> None:
        if isinstance(field_value, dict):
            if "value" in field_value and field_value["value"] is not None:
                if "data_source" not in field_value:
                    errors.append(f"Field '{field_name}' has value but no data_source")
                elif not field_value["data_source"].get("block_id"):
                    errors.append(f"Field '{field_name}' has data_source but no block_id")

            # Check nested fields
            for key, value in field_value.items():
                if key not in ("value", "data_source", "confidence"):
                    check_field(f"{field_name}.{key}", value)

    for field_name, field_value in result.items():
        check_field(field_name, field_value)

    return errors
