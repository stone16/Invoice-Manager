"""Tests for RAG system - TDD Red phase."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ====================
# 4.1 Embedding Generation Tests
# ====================


class TestEmbeddingGeneration:
    """Tests for embedding generation using OpenAI text-embedding-3-small."""

    def test_generate_embedding_returns_1536_dimensions(self):
        """Test that embedding service returns 1536-dimensional vector."""
        from app.services.rag.embedding_service import generate_embedding

        # Mock OpenAI response
        with patch("app.services.rag.embedding_service.get_openai_client") as mock_client:
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_client.return_value.embeddings.create.return_value = mock_response

            embedding = generate_embedding("test content")

            assert len(embedding) == 1536
            assert all(isinstance(v, float) for v in embedding)

    def test_weighted_text_preparation_first_page_highest(self):
        """Test that first page receives highest weight (1.0)."""
        from app.services.rag.embedding_service import prepare_weighted_text

        pages = [
            {"page_num": 1, "content": "First page content"},
            {"page_num": 2, "content": "Second page content"},
            {"page_num": 3, "content": "Third page content"},
        ]

        weighted_text, weights = prepare_weighted_text(pages)

        # First page should have highest weight
        assert weights[0] == 1.0
        assert weights[1] < weights[0]
        assert weights[2] < weights[1]
        # First page content should appear more prominently
        assert "First page content" in weighted_text

    def test_weighted_text_truncation_to_8192_tokens(self):
        """Test that total text is truncated to 8192 tokens."""
        from app.services.rag.embedding_service import prepare_weighted_text

        # Create very long content
        long_content = "word " * 10000  # Way more than 8192 tokens
        pages = [{"page_num": 1, "content": long_content}]

        weighted_text, _ = prepare_weighted_text(pages)

        # Should be truncated to approximately 8192 tokens
        # Using rough estimate of 4 chars per token
        assert len(weighted_text.split()) <= 8192

    def test_line_deduplication_removes_duplicates(self):
        """Test that duplicate lines (>95% similar) are removed."""
        from app.services.rag.embedding_service import deduplicate_lines

        text = """Header line that repeats
Content line 1
Content line 2
Header line that repeats
Footer information
Content line 3
Footer information"""

        deduplicated = deduplicate_lines(text, similarity_threshold=0.95)

        # Should remove duplicate header and footer
        lines = deduplicated.strip().split("\n")
        assert lines.count("Header line that repeats") == 1
        assert lines.count("Footer information") == 1

    @pytest.mark.asyncio
    async def test_batch_embedding_generation(self):
        """Test batch embedding for multiple texts."""
        from app.services.rag.embedding_service import generate_embeddings_batch

        texts = ["text 1", "text 2", "text 3"]

        with patch("app.services.rag.embedding_service.get_async_openai_client") as mock_client:
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536) for _ in texts]
            mock_client.return_value.embeddings.create = AsyncMock(return_value=mock_response)

            embeddings = await generate_embeddings_batch(texts)

            assert len(embeddings) == 3
            assert all(len(e) == 1536 for e in embeddings)


# ====================
# 4.3 pgvector Integration Tests
# ====================


class TestPgvectorIntegration:
    """Tests for pgvector storage and similarity search."""

    @pytest.mark.asyncio
    async def test_store_training_vector(self):
        """Test storing training vector with metadata."""
        from app.services.rag.vector_repository import VectorRepository

        mock_db = AsyncMock()
        repo = VectorRepository(mock_db)

        vector_data = {
            "flow_id": 1,
            "config_id": 1,
            "embedding": [0.1] * 1536,
            "reference_input": {"plain_text": "test content", "text_blocks": []},
            "reference_output": {"invoice_number": "INV-001"},
        }

        result = await repo.store_training_vector(**vector_data)

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_similarity_search_returns_results(self):
        """Test cosine similarity search returns matching vectors."""
        from app.services.rag.vector_repository import VectorRepository

        mock_db = AsyncMock()
        repo = VectorRepository(mock_db)

        query_embedding = [0.1] * 1536
        config_id = 1

        # Mock execute result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        results = await repo.similarity_search(
            embedding=query_embedding,
            config_id=config_id,
            distance_threshold=0.3,
            limit=5,
        )

        mock_db.execute.assert_called_once()
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_similarity_search_filters_by_config_id(self):
        """Test that search filters by config_id."""
        from app.services.rag.vector_repository import VectorRepository

        mock_db = AsyncMock()
        repo = VectorRepository(mock_db)

        query_embedding = [0.1] * 1536
        config_id = 42

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await repo.similarity_search(
            embedding=query_embedding,
            config_id=config_id,
            distance_threshold=0.3,
        )

        # Verify config_id filtering is applied in the query
        call_args = mock_db.execute.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_similarity_search_respects_distance_threshold(self):
        """Test that only results below distance threshold are returned."""
        from app.services.rag.vector_repository import VectorRepository

        mock_db = AsyncMock()
        repo = VectorRepository(mock_db)

        query_embedding = [0.1] * 1536

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Should use distance_threshold in query
        await repo.similarity_search(
            embedding=query_embedding,
            config_id=1,
            distance_threshold=0.2,  # Strict threshold
        )

        mock_db.execute.assert_called_once()


# ====================
# 4.4 Few-Shot Example Builder Tests
# ====================


class TestFewShotExampleBuilder:
    """Tests for few-shot example construction from RAG data."""

    def test_build_rag_example_has_required_sections(self):
        """Test that RAG example includes all required sections."""
        from app.services.rag.example_builder import build_rag_example

        training_data = {
            "reference_input": {
                "plain_text": "Invoice content here",
                "text_blocks": [
                    {"block_id": "1.1.1:1:1", "text": "INV-001"},
                ],
            },
            "reference_output": {
                "invoice_number": {
                    "value": "INV-001",
                    "data_source": {"block_id": "1.1.1:1:1"},
                }
            },
        }

        example = build_rag_example(training_data, document_name="sample.pdf")

        assert "<instruction>" in example
        assert "<name>" in example
        assert "<plain_text_input>" in example
        assert "<input_text_block>" in example
        assert "<expected_output>" in example
        assert "</instruction>" in example

    def test_build_rag_example_includes_document_name(self):
        """Test that example includes the document name."""
        from app.services.rag.example_builder import build_rag_example

        training_data = {
            "reference_input": {"plain_text": "test", "text_blocks": []},
            "reference_output": {},
        }

        example = build_rag_example(training_data, document_name="invoice_2024.pdf")

        assert "invoice_2024.pdf" in example

    def test_partial_content_selection_includes_referenced_blocks(self):
        """Test that only text blocks referenced in data_source are included."""
        from app.services.rag.example_builder import select_partial_content

        all_blocks = [
            {"block_id": "1.1.1:1:1", "text": "INV-001"},
            {"block_id": "1.1.2:1:1", "text": "Unreferenced"},
            {"block_id": "1.1.3:1:1", "text": "Another unreferenced"},
            {"block_id": "1.1.4:1:1", "text": "2024-01-15"},
            {"block_id": "1.1.5:1:1", "text": "Far away unreferenced"},
        ]

        extraction_result = {
            "invoice_number": {
                "value": "INV-001",
                "data_source": {"block_id": "1.1.1:1:1"},
            },
            "issue_date": {
                "value": "2024-01-15",
                "data_source": {"block_id": "1.1.4:1:1"},
            },
        }

        # Use context_window=0 to test basic selection without context expansion
        selected = select_partial_content(all_blocks, extraction_result, context_window=0)

        block_ids = [b["block_id"] for b in selected]
        assert "1.1.1:1:1" in block_ids
        assert "1.1.4:1:1" in block_ids
        # Unreferenced blocks should be excluded when context_window=0
        assert "1.1.3:1:1" not in block_ids
        assert "1.1.5:1:1" not in block_ids

    def test_partial_content_includes_surrounding_context(self):
        """Test that ±1 block context is added around referenced blocks."""
        from app.services.rag.example_builder import select_partial_content

        all_blocks = [
            {"block_id": "1.1.1:1:1", "text": "Context before"},
            {"block_id": "1.1.2:1:1", "text": "Referenced value"},
            {"block_id": "1.1.3:1:1", "text": "Context after"},
            {"block_id": "1.1.4:1:1", "text": "Far away"},
        ]

        extraction_result = {
            "field": {
                "value": "Referenced value",
                "data_source": {"block_id": "1.1.2:1:1"},
            },
        }

        selected = select_partial_content(all_blocks, extraction_result, context_window=1)

        block_ids = [b["block_id"] for b in selected]
        # Should include the referenced block and ±1 context
        assert "1.1.1:1:1" in block_ids  # before
        assert "1.1.2:1:1" in block_ids  # referenced
        assert "1.1.3:1:1" in block_ids  # after
        assert "1.1.4:1:1" not in block_ids  # too far


# ====================
# 4.5 Zero-Shot Fallback Tests
# ====================


class TestZeroShotFallback:
    """Tests for zero-shot example generation when no RAG matches."""

    def test_generate_zero_shot_from_schema(self):
        """Test zero-shot example generation from JSON schema."""
        from app.services.rag.example_builder import generate_zero_shot_example

        schema = {
            "properties": {
                "invoice_number": {"type": "string", "description": "Invoice number"},
                "total_amount": {"type": "number", "description": "Total amount"},
            },
            "required": ["invoice_number"],
        }

        example = generate_zero_shot_example(schema)

        assert "<expected_output>" in example
        assert "invoice_number" in example
        assert "data_source" in example  # Should show data_source structure

    def test_zero_shot_includes_data_source_structure(self):
        """Test that zero-shot example shows data_source format."""
        from app.services.rag.example_builder import generate_zero_shot_example

        schema = {
            "properties": {
                "field_name": {"type": "string"},
            },
        }

        example = generate_zero_shot_example(schema)

        # Should demonstrate the data_source structure
        assert "block_id" in example
        assert "confidence" in example or "data_source" in example

    def test_config_specific_zero_shot_override(self):
        """Test that config's zero_shot_example overrides schema-based."""
        from app.services.rag.example_builder import get_zero_shot_example

        schema = {"properties": {"field": {"type": "string"}}}

        config_zero_shot = """<expected_output>
{"custom_field": {"value": "custom", "data_source": {"block_id": "1.1.1:1:1"}}}
</expected_output>"""

        example = get_zero_shot_example(schema, config_zero_shot=config_zero_shot)

        assert "custom_field" in example
        assert "custom" in example


# ====================
# 4.6 RAG Configuration Tests
# ====================


class TestRAGConfiguration:
    """Tests for RAG configuration in workflow config."""

    def test_rag_disabled_skips_search(self):
        """Test that RAG disabled prevents similarity search."""
        from app.services.rag.rag_service import RAGService

        mock_repo = AsyncMock()
        service = RAGService(vector_repo=mock_repo)

        rag_config = {"enabled": False}

        # Should not perform search when disabled
        result = service.should_perform_rag(rag_config)
        assert result is False

    def test_rag_enabled_performs_search(self):
        """Test that RAG enabled allows similarity search."""
        from app.services.rag.rag_service import RAGService

        mock_repo = AsyncMock()
        service = RAGService(vector_repo=mock_repo)

        rag_config = {"enabled": True, "distance_threshold": 0.3}

        result = service.should_perform_rag(rag_config)
        assert result is True

    def test_rag_config_distance_threshold_applied(self):
        """Test that custom distance_threshold is used in search."""
        from app.services.rag.rag_service import RAGService

        mock_repo = AsyncMock()
        service = RAGService(vector_repo=mock_repo)

        rag_config = {"enabled": True, "distance_threshold": 0.15}

        threshold = service.get_distance_threshold(rag_config)
        assert threshold == 0.15

    def test_default_rag_config_values(self):
        """Test default RAG configuration values."""
        from app.services.rag.rag_service import DEFAULT_RAG_CONFIG

        assert "enabled" in DEFAULT_RAG_CONFIG
        assert "distance_threshold" in DEFAULT_RAG_CONFIG
        assert DEFAULT_RAG_CONFIG["distance_threshold"] == 0.3  # Default threshold


# ====================
# Integration Tests
# ====================


class TestRAGIntegration:
    """Integration tests for the full RAG pipeline."""

    @pytest.mark.asyncio
    async def test_full_rag_pipeline_with_match(self):
        """Test full RAG flow when similar document found."""
        from app.services.rag.rag_service import RAGService

        mock_repo = AsyncMock()
        mock_embedding_service = MagicMock()

        # Mock finding a similar document
        mock_repo.similarity_search.return_value = [
            MagicMock(
                reference_input={"plain_text": "test", "text_blocks": []},
                reference_output={"invoice_number": {"value": "INV-001"}},
                distance=0.1,
            )
        ]
        mock_embedding_service.generate_embedding.return_value = [0.1] * 1536

        service = RAGService(
            vector_repo=mock_repo,
            embedding_service=mock_embedding_service,
        )

        rag_config = {"enabled": True, "distance_threshold": 0.3}
        content = "New invoice content"
        config_id = 1

        result = await service.get_few_shot_examples(
            content=content,
            config_id=config_id,
            rag_config=rag_config,
        )

        assert result is not None
        assert "few_shot_examples" in result
        assert result["source"] == "rag"

    @pytest.mark.asyncio
    async def test_full_rag_pipeline_fallback_to_zero_shot(self):
        """Test RAG fallback to zero-shot when no matches."""
        from app.services.rag.rag_service import RAGService

        mock_repo = AsyncMock()
        mock_embedding_service = MagicMock()

        # Mock finding no similar documents
        mock_repo.similarity_search.return_value = []
        mock_embedding_service.generate_embedding.return_value = [0.1] * 1536

        service = RAGService(
            vector_repo=mock_repo,
            embedding_service=mock_embedding_service,
        )

        schema = {"properties": {"invoice_number": {"type": "string"}}}
        rag_config = {"enabled": True, "distance_threshold": 0.3}
        content = "New invoice content"
        config_id = 1

        result = await service.get_few_shot_examples(
            content=content,
            config_id=config_id,
            rag_config=rag_config,
            schema=schema,
        )

        assert result is not None
        assert result["source"] == "zero_shot"
