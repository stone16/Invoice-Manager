"""LLM Integration module for document digitization."""

from app.services.llm.client_factory import (
    DEFAULT_MODEL_CONFIG,
    build_model_kwargs,
    create_llm_client,
    get_supported_providers,
)
from app.services.llm.executor import (
    BatchDigitizationExecutor,
    DigitizationExecutor,
    get_langsmith_run_id,
)
from app.services.llm.prompt_engine import (
    build_system_prompt,
    build_user_prompt,
    format_schema_for_prompt,
)
from app.services.llm.structured_output import (
    build_extraction_response,
    extract_json_from_text,
    normalize_result,
    parse_extraction_result,
)
from app.services.llm.validation import (
    extract_block_ids_from_result,
    validate_block_id,
    validate_data_source_completeness,
    validate_extraction_result,
    validate_required_fields,
)

__all__ = [
    # Client factory
    "DEFAULT_MODEL_CONFIG",
    "build_model_kwargs",
    "create_llm_client",
    "get_supported_providers",
    # Executor
    "DigitizationExecutor",
    "BatchDigitizationExecutor",
    "get_langsmith_run_id",
    # Prompt engine
    "build_system_prompt",
    "build_user_prompt",
    "format_schema_for_prompt",
    # Structured output
    "parse_extraction_result",
    "extract_json_from_text",
    "normalize_result",
    "build_extraction_response",
    # Validation
    "validate_block_id",
    "validate_extraction_result",
    "extract_block_ids_from_result",
    "validate_required_fields",
    "validate_data_source_completeness",
]
