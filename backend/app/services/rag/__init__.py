"""RAG (Retrieval-Augmented Generation) system for few-shot examples."""

from app.services.rag.embedding_service import (
    deduplicate_lines,
    generate_embedding,
    generate_embeddings_batch,
    prepare_weighted_text,
    truncate_to_tokens,
)
from app.services.rag.example_builder import (
    build_rag_example,
    format_few_shot_examples,
    generate_zero_shot_example,
    get_zero_shot_example,
    select_partial_content,
)
from app.services.rag.rag_service import (
    DEFAULT_RAG_CONFIG,
    RAGService,
)
from app.services.rag.vector_repository import VectorRepository

__all__ = [
    # Embedding service
    "generate_embedding",
    "generate_embeddings_batch",
    "prepare_weighted_text",
    "truncate_to_tokens",
    "deduplicate_lines",
    # Example builder
    "build_rag_example",
    "format_few_shot_examples",
    "generate_zero_shot_example",
    "get_zero_shot_example",
    "select_partial_content",
    # RAG service
    "RAGService",
    "DEFAULT_RAG_CONFIG",
    # Vector repository
    "VectorRepository",
]
