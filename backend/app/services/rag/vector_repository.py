"""Repository for RAG training data vector operations with pgvector."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy import literal_column, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.digi_flow import RagTrainingDataVector


@dataclass(frozen=True)
class VectorSearchResult:
    """Typed result for similarity search responses."""

    vector: RagTrainingDataVector
    distance: float


class VectorRepository:
    """Repository for pgvector operations on training data."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        Args:
            db: AsyncSession for database operations.
        """
        self.db = db

    async def store_training_vector(
        self,
        flow_id: int,
        config_id: int,
        embedding: List[float],
        reference_input: Dict[str, Any],
        reference_output: Dict[str, Any],
        schema_id: int = 0,
        schema_version: int = 1,
        result_id: int = 0,
        result_version: int = 1,
        source_content_context: Optional[Dict[str, Any]] = None,
        source_content_context_idx: int = 0,
    ) -> RagTrainingDataVector:
        """Store a training vector with metadata.

        Args:
            flow_id: Reference to extraction flow.
            config_id: Reference to config used.
            embedding: 1536-dimensional embedding vector.
            reference_input: JSONB with plain_text and text_blocks.
            reference_output: JSONB with extraction result.
            schema_id: Reference to schema.
            schema_version: Schema version.
            result_id: Reference to result.
            result_version: Result version.
            source_content_context: Source content context.
            source_content_context_idx: Index in source content.

        Returns:
            Created RagTrainingDataVector record.
        """
        vector = RagTrainingDataVector(
            flow_id=flow_id,
            config_id=config_id,
            schema_id=schema_id,
            schema_version=schema_version,
            result_id=result_id,
            result_version=result_version,
            source_content_context=source_content_context or {},
            source_content_context_idx=source_content_context_idx,
            reference_input=reference_input,
            reference_output=reference_output,
            embedding=embedding,
        )

        self.db.add(vector)
        await self.db.flush()
        await self.db.refresh(vector)

        return vector

    async def similarity_search(
        self,
        embedding: List[float],
        config_id: int,
        distance_threshold: float = 0.3,
        limit: int = 5,
    ) -> List[VectorSearchResult]:
        """Perform cosine similarity search for similar vectors.

        Args:
            embedding: Query embedding vector.
            config_id: Filter by config ID.
            distance_threshold: Maximum cosine distance for matches.
            limit: Maximum number of results to return.

        Returns:
            List of matching RagTrainingDataVector records.
        """
        # Build raw SQL for pgvector cosine distance search
        # Using 1 - (embedding <=> query_embedding) for cosine similarity
        # <=> is the cosine distance operator in pgvector

        embedding_str = json.dumps(embedding)

        query = text(
            """
            SELECT *,
                   (embedding <=> :embedding::vector) as distance
            FROM rag_training_data_vector
            WHERE config_id = :config_id
              AND (embedding <=> :embedding::vector) < :threshold
            ORDER BY distance ASC
            LIMIT :limit
            """
        )

        statement = select(
            RagTrainingDataVector,
            literal_column("distance"),
        ).from_statement(query)

        result = await self.db.execute(
            statement,
            {
                "embedding": embedding_str,
                "config_id": config_id,
                "threshold": distance_threshold,
                "limit": limit,
            },
        )

        rows = result.all()

        return [
            VectorSearchResult(vector=row[0], distance=row[1])
            for row in rows
        ]

    async def get_by_flow_id(
        self,
        flow_id: int,
    ) -> List[RagTrainingDataVector]:
        """Get all training vectors for a specific flow.

        Args:
            flow_id: The flow ID to search for.

        Returns:
            List of matching vectors.
        """
        query = select(RagTrainingDataVector).where(
            RagTrainingDataVector.flow_id == flow_id
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_config_id(
        self,
        config_id: int,
        limit: int = 100,
    ) -> List[RagTrainingDataVector]:
        """Get training vectors for a specific config.

        Args:
            config_id: The config ID to filter by.
            limit: Maximum number of results.

        Returns:
            List of matching vectors.
        """
        query = (
            select(RagTrainingDataVector)
            .where(RagTrainingDataVector.config_id == config_id)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_by_flow_id(
        self,
        flow_id: int,
    ) -> int:
        """Delete all training vectors for a specific flow.

        Args:
            flow_id: The flow ID to delete vectors for.

        Returns:
            Number of deleted records.
        """
        from sqlalchemy import delete

        query = delete(RagTrainingDataVector).where(
            RagTrainingDataVector.flow_id == flow_id
        )
        result = await self.db.execute(query)
        return result.rowcount or 0
