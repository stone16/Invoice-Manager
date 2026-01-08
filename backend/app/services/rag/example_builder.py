"""Few-shot example builder for RAG system."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set


def build_rag_example(
    training_data: Dict[str, Any],
    document_name: str = "document",
) -> str:
    """Build a RAG example prompt from training data.

    The example includes:
    - <instruction> explaining the mapping rules
    - <name> with document name
    - <plain_text_input> with page content
    - <input_text_block> with text blocks
    - <expected_output> with extraction result

    Args:
        training_data: Training data with reference_input and reference_output.
        document_name: Name of the document.

    Returns:
        Formatted example string with XML sections.
    """
    reference_input = training_data.get("reference_input", {})
    reference_output = training_data.get("reference_output", {})

    plain_text = reference_input.get("plain_text", "")
    text_blocks = reference_input.get("text_blocks", [])

    # Build text blocks section
    text_blocks_str = ""
    for block in text_blocks:
        block_id = block.get("block_id", "")
        text = block.get("text", "")
        text_blocks_str += f'<block id="{block_id}">{text}</block>\n'

    # Format the expected output
    output_json = json.dumps(reference_output, ensure_ascii=False, indent=2)

    example = f"""<instruction>
Extract structured data from the document. Map each field value to its source text block using the block_id.
The data_source field should contain the block_id where the value was found, along with confidence if available.
</instruction>

<name>{document_name}</name>

<plain_text_input>
{plain_text}
</plain_text_input>

<input_text_block>
{text_blocks_str.strip()}
</input_text_block>

<expected_output>
{output_json}
</expected_output>"""

    return example


def select_partial_content(
    all_blocks: List[Dict[str, Any]],
    extraction_result: Dict[str, Any],
    context_window: int = 1,
) -> List[Dict[str, Any]]:
    """Select only text blocks referenced in extraction result plus surrounding context.

    Args:
        all_blocks: All text blocks from the document.
        extraction_result: The extraction result with data_source references.
        context_window: Number of surrounding blocks to include (±N).

    Returns:
        Filtered list of blocks with referenced blocks and context.
    """
    if not all_blocks:
        return []

    # Extract all referenced block IDs from the extraction result
    referenced_ids = _extract_block_ids(extraction_result)

    # Build index of block positions
    block_positions: Dict[str, int] = {}
    for i, block in enumerate(all_blocks):
        block_id = block.get("block_id", "")
        if block_id:
            block_positions[block_id] = i

    # Find positions that need to be included
    positions_to_include: Set[int] = set()

    for block_id in referenced_ids:
        if block_id in block_positions:
            pos = block_positions[block_id]
            # Add the referenced block and surrounding context
            for offset in range(-context_window, context_window + 1):
                context_pos = pos + offset
                if 0 <= context_pos < len(all_blocks):
                    positions_to_include.add(context_pos)

    # Build result maintaining order
    result = []
    for i, block in enumerate(all_blocks):
        if i in positions_to_include:
            result.append(block)

    return result


def _extract_block_ids(obj: Any, block_ids: Optional[Set[str]] = None) -> Set[str]:
    """Recursively extract all block_id values from an object.

    Args:
        obj: Object to extract block IDs from.
        block_ids: Set to accumulate block IDs.

    Returns:
        Set of block IDs found.
    """
    if block_ids is None:
        block_ids = set()

    if isinstance(obj, dict):
        # Check for data_source.block_id pattern
        if "data_source" in obj and isinstance(obj["data_source"], dict):
            data_source = obj["data_source"]
            if "block_id" in data_source and data_source["block_id"]:
                block_ids.add(data_source["block_id"])

        # Also check direct block_id
        if "block_id" in obj and obj["block_id"]:
            block_ids.add(obj["block_id"])

        # Recurse into all values
        for value in obj.values():
            _extract_block_ids(value, block_ids)

    elif isinstance(obj, list):
        for item in obj:
            _extract_block_ids(item, block_ids)

    return block_ids


def generate_zero_shot_example(schema: Dict[str, Any]) -> str:
    """Generate a zero-shot example from JSON schema.

    Shows the expected output format with data_source structure.

    Args:
        schema: JSON schema definition.

    Returns:
        Zero-shot example string.
    """
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    # Build sample output structure
    sample_output: Dict[str, Any] = {}

    for field_name, field_def in properties.items():
        field_type = field_def.get("type", "string")

        # Generate sample value based on type
        if field_type == "string":
            sample_value = f"<{field_name}_value>"
        elif field_type == "number":
            sample_value = 0.0
        elif field_type == "integer":
            sample_value = 0
        elif field_type == "boolean":
            sample_value = False
        elif field_type == "array":
            sample_value = []
        elif field_type == "object":
            sample_value = {}
        else:
            sample_value = None

        # All fields get data_source structure for lineage
        sample_output[field_name] = {
            "value": sample_value,
            "data_source": {
                "block_id": "<block_id_where_value_found>",
                "confidence": 0.95,
                "extraction_method": "llm",
            },
        }

    output_json = json.dumps(sample_output, ensure_ascii=False, indent=2)

    return f"""<instruction>
Extract structured data from the document. For each field, find the value in the text blocks
and record the block_id where it was found in the data_source field.
</instruction>

<expected_output>
{output_json}
</expected_output>"""


def get_zero_shot_example(
    schema: Dict[str, Any],
    config_zero_shot: Optional[str] = None,
) -> str:
    """Get zero-shot example, preferring config override if available.

    Args:
        schema: JSON schema definition.
        config_zero_shot: Optional config-specific zero-shot example.

    Returns:
        Zero-shot example string.
    """
    if config_zero_shot:
        return config_zero_shot

    return generate_zero_shot_example(schema)


def format_few_shot_examples(
    examples: List[Dict[str, Any]],
    max_examples: int = 1,
) -> str:
    """Format multiple few-shot examples for the prompt.

    Args:
        examples: List of training data examples.
        max_examples: Maximum number of examples to include.

    Returns:
        Formatted examples string.
    """
    if not examples:
        return ""

    # Take only up to max_examples, sorted by distance (if available)
    sorted_examples = sorted(
        examples,
        key=lambda x: x.get("distance", float("inf")),
    )[:max_examples]

    formatted_parts = []
    for i, example in enumerate(sorted_examples, 1):
        doc_name = example.get("document_name", f"example_{i}")
        formatted = build_rag_example(example, document_name=doc_name)
        formatted_parts.append(f"--- Example {i} ---\n{formatted}")

    return "\n\n".join(formatted_parts)
