"""Main RAG service orchestrating embedding, search, and example construction."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.rag.example_builder import (
    build_rag_example,
    format_few_shot_examples,
    get_zero_shot_example,
    select_partial_content,
)
from app.services.rag.vector_repository import VectorRepository


# Default RAG configuration values
DEFAULT_RAG_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "distance_threshold": 0.3,
    "max_examples": 1,
    "training_data_source_fields": ["plain_text", "text_blocks"],
    "training_data_reference_fields": ["output_values", "data_source_info"],
}


class RAGService:
    """Service for RAG-based few-shot example retrieval."""

    def __init__(
        self,
        vector_repo: Optional[VectorRepository] = None,
        embedding_service: Optional[Any] = None,
    ):
        """Initialize RAG service.

        Args:
            vector_repo: Repository for vector operations.
            embedding_service: Service for generating embeddings.
        """
        self.vector_repo = vector_repo
        self.embedding_service = embedding_service

    def should_perform_rag(self, rag_config: Optional[Dict[str, Any]] = None) -> bool:
        """Check if RAG should be performed based on config.

        Args:
            rag_config: RAG configuration dict.

        Returns:
            True if RAG is enabled and should be performed.
        """
        if rag_config is None:
            rag_config = DEFAULT_RAG_CONFIG

        return rag_config.get("enabled", DEFAULT_RAG_CONFIG["enabled"])

    def get_distance_threshold(
        self,
        rag_config: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Get the distance threshold from config.

        Args:
            rag_config: RAG configuration dict.

        Returns:
            Distance threshold value.
        """
        if rag_config is None:
            rag_config = DEFAULT_RAG_CONFIG

        return rag_config.get(
            "distance_threshold",
            DEFAULT_RAG_CONFIG["distance_threshold"],
        )

    async def get_few_shot_examples(
        self,
        content: str,
        config_id: int,
        rag_config: Optional[Dict[str, Any]] = None,
        schema: Optional[Dict[str, Any]] = None,
        config_zero_shot: Optional[str] = None,
        text_blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Get few-shot examples for a document using RAG.

        First attempts to find similar documents via vector search.
        Falls back to zero-shot example if no matches found.

        Args:
            content: Document content for embedding.
            config_id: Config ID to filter training data.
            rag_config: RAG configuration.
            schema: JSON schema for zero-shot fallback.
            config_zero_shot: Config-specific zero-shot example.
            text_blocks: Text blocks from the document.

        Returns:
            Dict with 'few_shot_examples' and 'source' ('rag' or 'zero_shot').
        """
        if rag_config is None:
            rag_config = DEFAULT_RAG_CONFIG

        # Check if RAG is enabled
        if not self.should_perform_rag(rag_config):
            return self._get_zero_shot_result(schema, config_zero_shot)

        # Generate embedding for the document
        if self.embedding_service is None:
            from app.services.rag import embedding_service

            self.embedding_service = embedding_service

        embedding = self.embedding_service.generate_embedding(content)

        # Search for similar documents
        if self.vector_repo is None:
            return self._get_zero_shot_result(schema, config_zero_shot)

        distance_threshold = self.get_distance_threshold(rag_config)
        max_examples = rag_config.get("max_examples", 1)

        similar_docs = await self.vector_repo.similarity_search(
            embedding=embedding,
            config_id=config_id,
            distance_threshold=distance_threshold,
            limit=max_examples,
        )

        if not similar_docs:
            return self._get_zero_shot_result(schema, config_zero_shot)

        # Build few-shot examples from retrieved documents
        examples = []
        for doc in similar_docs:
            example_data = {
                "reference_input": doc.reference_input,
                "reference_output": doc.reference_output,
                "distance": getattr(doc, "distance", 0.0),
            }
            examples.append(example_data)

        formatted_examples = format_few_shot_examples(examples, max_examples)

        return {
            "few_shot_examples": formatted_examples,
            "source": "rag",
            "match_count": len(similar_docs),
            "best_distance": getattr(similar_docs[0], "distance", 0.0)
            if similar_docs
            else None,
        }

    def _get_zero_shot_result(
        self,
        schema: Optional[Dict[str, Any]],
        config_zero_shot: Optional[str],
    ) -> Dict[str, Any]:
        """Get zero-shot fallback result.

        Args:
            schema: JSON schema for generating example.
            config_zero_shot: Config-specific zero-shot example.

        Returns:
            Zero-shot result dict.
        """
        if schema is None:
            schema = {"properties": {}}

        example = get_zero_shot_example(schema, config_zero_shot)

        return {
            "few_shot_examples": example,
            "source": "zero_shot",
            "match_count": 0,
            "best_distance": None,
        }

    async def store_training_data(
        self,
        flow_id: int,
        config_id: int,
        content: str,
        extraction_result: Dict[str, Any],
        text_blocks: Optional[List[Dict[str, Any]]] = None,
        schema_id: int = 0,
        schema_version: int = 1,
        result_id: int = 0,
        result_version: int = 1,
    ) -> Optional[Any]:
        """Store confirmed extraction as training data.

        Args:
            flow_id: Flow ID reference.
            config_id: Config ID reference.
            content: Document content for embedding.
            extraction_result: The confirmed extraction result.
            text_blocks: Text blocks from the document.
            schema_id: Schema ID reference.
            schema_version: Schema version.
            result_id: Result ID reference.
            result_version: Result version.

        Returns:
            Created training vector or None.
        """
        if self.vector_repo is None:
            return None

        # Generate embedding
        if self.embedding_service is None:
            from app.services.rag import embedding_service

            self.embedding_service = embedding_service

        embedding = self.embedding_service.generate_embedding(content)

        # Select partial content for reference_input
        all_blocks = text_blocks or []
        selected_blocks = select_partial_content(all_blocks, extraction_result)

        reference_input = {
            "plain_text": content[:5000],  # Truncate for storage
            "text_blocks": selected_blocks,
        }

        reference_output = extraction_result

        return await self.vector_repo.store_training_vector(
            flow_id=flow_id,
            config_id=config_id,
            schema_id=schema_id,
            schema_version=schema_version,
            result_id=result_id,
            result_version=result_version,
            embedding=embedding,
            reference_input=reference_input,
            reference_output=reference_output,
        )
