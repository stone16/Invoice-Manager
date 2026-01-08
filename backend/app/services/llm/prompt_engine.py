"""Prompt engine for building system and user prompts for digitization."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def build_system_prompt(
    prompt_config: Dict[str, Any],
    schema: Dict[str, Any],
    few_shot_example: Optional[str] = None,
) -> str:
    """Build the system prompt for digitization.

    Args:
        prompt_config: Configuration containing task and instructions.
        schema: JSON schema for the extraction output.
        few_shot_example: Optional few-shot example from RAG or zero-shot.

    Returns:
        Complete system prompt string.
    """
    parts = []

    # Role and objective
    task = prompt_config.get("task", "Extract structured data from document")
    parts.append(f"""You are an expert document digitization assistant.
Your role is to accurately extract structured data from documents.

## Objective
{task}
""")

    # Source mapping protocol
    parts.append("""## Source Mapping Protocol

For every extracted value, you MUST provide a data_source with block_id pointing to the exact text block where the value was found.

Rules for block_id mapping:
- The block_id must reference the text block containing the actual VALUE, not the label
- For example, if extracting an invoice number from "Invoice Number: INV-001", point to the block containing "INV-001", not "Invoice Number:"
- Every field with a value MUST have a corresponding data_source with block_id
- If a value spans multiple blocks, reference the primary block containing the value

## Value vs Label Rule

IMPORTANT: Always point the block_id to the VALUE, not the LABEL.
- WRONG: Pointing to "Total Amount:" (label)
- RIGHT: Pointing to "$1,234.56" (value)
""")

    # Custom instructions
    custom_instructions = prompt_config.get("instructions", "")
    if custom_instructions:
        parts.append(f"""## Custom Instructions

{custom_instructions}
""")

    # Schema information
    if schema:
        schema_str = json.dumps(schema, indent=2)
        parts.append(f"""## Output Schema

Extract data according to this schema:
```json
{schema_str}
```
""")

    # Few-shot example
    if few_shot_example:
        parts.append(f"""## Example

{few_shot_example}
""")

    return "\n".join(parts)


def build_user_prompt(
    content: Dict[str, Any],
    document_name: str = "document",
) -> str:
    """Build the user prompt containing document content.

    Args:
        content: Document content with plain_text and text_blocks.
        document_name: Name of the document being processed.

    Returns:
        User prompt string with document content.
    """
    parts = []

    parts.append(f"""## Document: {document_name}

Please extract the required data from the following document content.
""")

    # Plain text content
    plain_text = content.get("plain_text", "")
    if plain_text:
        parts.append(f"""### Plain Text Content

{plain_text}
""")

    # Text blocks with IDs
    text_blocks = content.get("text_blocks", [])
    if text_blocks:
        parts.append("### Text Blocks with IDs\n")
        for block in text_blocks:
            block_id = block.get("block_id", "unknown")
            text = block.get("text", "")
            parts.append(f"[{block_id}] {text}")
        parts.append("")

    parts.append("""### Instructions

Extract all relevant fields and provide block_id references for each extracted value.
Return the result as valid JSON matching the schema provided.
""")

    return "\n".join(parts)


def format_schema_for_prompt(schema: Dict[str, Any]) -> str:
    """Format JSON schema for inclusion in prompt.

    Args:
        schema: JSON schema dictionary.

    Returns:
        Formatted schema string.
    """
    return json.dumps(schema, indent=2)
