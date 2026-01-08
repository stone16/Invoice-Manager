"""Token Optimization module for reducing LLM costs."""

from app.services.token_optimization.deduplication import (
    SIMILARITY_THRESHOLD,
    calculate_line_similarity,
    deduplicate_text,
    remove_duplicated_lines,
)
from app.services.token_optimization.encoder import (
    count_tokens,
    decode_tokens,
    encode_text,
    get_encoder,
    truncate_to_tokens,
)
from app.services.token_optimization.optimizer import (
    build_weighted_embedding_text,
    estimate_token_savings,
    optimize_for_embedding,
    optimize_for_prompt,
)
from app.services.token_optimization.truncation import (
    allocate_tokens,
    apply_weighted_truncation,
    calculate_page_weights,
    is_xml_tag,
    truncate_with_tags,
)

__all__ = [
    # Encoder
    "get_encoder",
    "count_tokens",
    "encode_text",
    "decode_tokens",
    "truncate_to_tokens",
    # Deduplication
    "SIMILARITY_THRESHOLD",
    "remove_duplicated_lines",
    "calculate_line_similarity",
    "deduplicate_text",
    # Truncation
    "is_xml_tag",
    "calculate_page_weights",
    "allocate_tokens",
    "truncate_with_tags",
    "apply_weighted_truncation",
    # Optimizer
    "optimize_for_embedding",
    "optimize_for_prompt",
    "build_weighted_embedding_text",
    "estimate_token_savings",
]
