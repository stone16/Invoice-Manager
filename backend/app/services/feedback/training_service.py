"""Service for RAG training data generation and management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set


def validate_training_data(training_data: Dict[str, Any]) -> List[str]:
    """Validate training data quality.

    Args:
        training_data: Training data to validate.

    Returns:
        List of validation errors, empty if valid.
    """
    errors = []

    # Check reference input is not empty
    reference_input = training_data.get("reference_input", {})
    if not reference_input or (
        not reference_input.get("plain_text") and not reference_input.get("text_blocks")
    ):
        errors.append("Reference input is empty or missing required content")

    # Check reference output exists
    reference_output = training_data.get("reference_output", {})
    if not reference_output:
        errors.append("Reference output is empty")

    # Check embedding dimensions (must be 1536 for OpenAI embeddings)
    embedding = training_data.get("embedding", [])
    if len(embedding) != 1536:
        errors.append(f"Embedding must have 1536 dimensions, got {len(embedding)}")

    # Check that all block_ids in output exist in input
    input_block_ids = _extract_input_block_ids(reference_input)
    output_block_ids = _extract_output_block_ids(reference_output)

    missing_block_ids = output_block_ids - input_block_ids
    if missing_block_ids:
        errors.append(
            f"block_id references in output not found in input: {missing_block_ids}"
        )

    return errors


def should_generate_training(
    extraction_result: Dict[str, Any],
    min_populated_ratio: float = 0.5,
) -> bool:
    """Determine if extraction result should generate training data.

    Args:
        extraction_result: The extraction result to evaluate.
        min_populated_ratio: Minimum ratio of populated fields required.

    Returns:
        True if training data should be generated.
    """
    if not extraction_result:
        return False

    total_fields = len(extraction_result)
    if total_fields == 0:
        return False

    populated_count = sum(
        1 for field in extraction_result.values()
        if isinstance(field, dict) and field.get("value") is not None
    )

    populated_ratio = populated_count / total_fields
    return populated_ratio >= min_populated_ratio


def _extract_input_block_ids(reference_input: Dict[str, Any]) -> Set[str]:
    """Extract all block IDs from input content."""
    block_ids = set()
    for block in reference_input.get("text_blocks", []):
        if "block_id" in block:
            block_ids.add(block["block_id"])
    return block_ids


def _extract_output_block_ids(reference_output: Dict[str, Any]) -> Set[str]:
    """Extract all block IDs referenced in output."""
    block_ids = set()

    def _traverse(obj: Any) -> None:
        """Traverse nested structures to collect block IDs."""
        if isinstance(obj, dict):
            if "data_source" in obj and "block_id" in obj["data_source"]:
                block_ids.add(obj["data_source"]["block_id"])
            for value in obj.values():
                _traverse(value)
        elif isinstance(obj, list):
            for item in obj:
                _traverse(item)

    _traverse(reference_output)
    return block_ids


class TrainingDataService:
    """Service for managing RAG training data."""

    def __init__(self, db: Any, embedding_service: Any = None):
        """Initialize training data service.

        Args:
            db: Database session.
            embedding_service: Optional embedding service for vector generation.
        """
        self.db = db
        self.embedding_service = embedding_service

    async def generate_training_data(
        self,
        flow_id: int,
        config_id: int,
        content: Dict[str, Any],
        extraction_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate training data from confirmed extraction.

        Args:
            flow_id: Flow ID reference.
            config_id: Configuration ID reference.
            content: Original document content.
            extraction_result: Confirmed extraction result.

        Returns:
            Generated training data record.
        """
        # Select only referenced blocks for partial content
        referenced_blocks = self.select_partial_content(
            content.get("text_blocks", []),
            extraction_result,
            context_window=1,
        )

        # Build reference input
        reference_input = {
            "plain_text": content.get("plain_text", ""),
            "text_blocks": referenced_blocks,
        }

        # Generate embedding if service available
        embedding = []
        if self.embedding_service:
            embedding_text = self._build_embedding_text(content, extraction_result)
            embedding = self.embedding_service.generate_embedding(embedding_text)

        training_data = {
            "flow_id": flow_id,
            "config_id": config_id,
            "reference_input": reference_input,
            "reference_output": extraction_result,
            "embedding": embedding,
            "created_at": datetime.utcnow().isoformat(),
        }

        # In real implementation, save to database
        # await self._save_training_data(training_data)

        return training_data

    async def update_training_data(
        self,
        flow_id: int,
        config_id: int,
        content: Dict[str, Any],
        extraction_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update existing training data after re-confirmation.

        Args:
            flow_id: Flow ID reference.
            config_id: Configuration ID reference.
            content: Original document content.
            extraction_result: Updated extraction result.

        Returns:
            Updated training data record.
        """
        # Check for existing training data
        existing = await self._get_existing_training_data(flow_id, config_id)

        # Select only referenced blocks
        referenced_blocks = self.select_partial_content(
            content.get("text_blocks", []),
            extraction_result,
            context_window=1,
        )

        # Build reference input
        reference_input = {
            "plain_text": content.get("plain_text", ""),
            "text_blocks": referenced_blocks,
        }

        # Generate new embedding if service available
        embedding = []
        if self.embedding_service:
            embedding_text = self._build_embedding_text(content, extraction_result)
            embedding = self.embedding_service.generate_embedding(embedding_text)

        updated_data = {
            "id": existing.id if existing else None,
            "flow_id": flow_id,
            "config_id": config_id,
            "reference_input": reference_input,
            "reference_output": extraction_result,
            "embedding": embedding,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # In real implementation, update database
        # await self._update_training_record(updated_data)

        return updated_data

    async def delete_training_data(self, flow_id: int) -> None:
        """Delete training data for a flow.

        Args:
            flow_id: Flow ID reference.
        """
        # TODO: Replace with real delete query.
        # In real implementation:
        # DELETE FROM digi_flow_training_data WHERE flow_id = :flow_id
        await self.db.execute(None)  # Mock deletion

    def select_partial_content(
        self,
        all_blocks: List[Dict[str, Any]],
        extraction_result: Dict[str, Any],
        context_window: int = 1,
    ) -> List[Dict[str, Any]]:
        """Select only referenced blocks plus context.

        Args:
            all_blocks: All text blocks from document.
            extraction_result: Extraction result with block references.
            context_window: Number of adjacent blocks to include.

        Returns:
            Selected blocks for training.
        """
        # Extract referenced block IDs
        referenced_ids = _extract_output_block_ids(extraction_result)

        if not referenced_ids:
            return []

        # Build index for blocks
        block_index = {b["block_id"]: i for i, b in enumerate(all_blocks)}

        # Find indices to include
        indices_to_include = set()
        for block_id in referenced_ids:
            if block_id in block_index:
                idx = block_index[block_id]
                # Add the block and context
                for offset in range(-context_window, context_window + 1):
                    if 0 <= idx + offset < len(all_blocks):
                        indices_to_include.add(idx + offset)

        # Return selected blocks in order
        return [all_blocks[i] for i in sorted(indices_to_include)]

    async def _get_existing_training_data(
        self, flow_id: int, config_id: int
    ) -> Optional[Any]:
        """Get existing training data for flow/config."""
        # TODO: Replace with real query.
        result = await self.db.execute(None)  # Mock query
        return result.scalar()

    def _build_embedding_text(
        self,
        content: Dict[str, Any],
        extraction_result: Dict[str, Any],
    ) -> str:
        """Build text for embedding generation."""
        # Combine content and result for semantic embedding
        parts = [content.get("plain_text", "")]

        for field_name, field_data in extraction_result.items():
            if isinstance(field_data, dict) and "value" in field_data:
                parts.append(f"{field_name}: {field_data['value']}")

        return " ".join(filter(None, parts))
