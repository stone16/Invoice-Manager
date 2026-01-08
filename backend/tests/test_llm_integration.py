"""Tests for LLM Integration - TDD Red phase."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

# Check if langchain is available
try:
    import langchain_core
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    import langchain_openai
    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError:
    LANGCHAIN_OPENAI_AVAILABLE = False


# ====================
# 5.1 Prompt Construction Tests
# ====================


class TestPromptEngine:
    """Tests for prompt construction."""

    def test_system_prompt_includes_role_and_objective(self):
        """Test that system prompt includes role and objective."""
        from app.services.llm.prompt_engine import build_system_prompt

        prompt_config = {
            "task": "Extract invoice data",
            "instructions": "Be precise with numbers",
        }

        prompt = build_system_prompt(prompt_config, schema={})

        assert "role" in prompt.lower() or "assistant" in prompt.lower()
        assert "extract" in prompt.lower()

    def test_system_prompt_includes_source_mapping_protocol(self):
        """Test that system prompt includes Block ID mapping rules."""
        from app.services.llm.prompt_engine import build_system_prompt

        prompt = build_system_prompt({}, schema={})

        # Should include source mapping protocol
        assert "block_id" in prompt.lower()
        assert "data_source" in prompt.lower()

    def test_system_prompt_includes_value_vs_label_rule(self):
        """Test that prompt includes rule about value vs label."""
        from app.services.llm.prompt_engine import build_system_prompt

        prompt = build_system_prompt({}, schema={})

        # Should include explicit rule about pointing to value not label
        assert "value" in prompt.lower()
        assert "label" in prompt.lower()

    def test_system_prompt_includes_custom_instructions(self):
        """Test that custom instructions from config are included."""
        from app.services.llm.prompt_engine import build_system_prompt

        prompt_config = {
            "instructions": "Always verify tax ID format",
        }

        prompt = build_system_prompt(prompt_config, schema={})

        assert "Always verify tax ID format" in prompt

    def test_system_prompt_includes_few_shot_example(self):
        """Test that few-shot example from RAG is included."""
        from app.services.llm.prompt_engine import build_system_prompt

        few_shot = """<expected_output>
{"invoice_number": {"value": "INV-001", "data_source": {"block_id": "1.1.1:1:1"}}}
</expected_output>"""

        prompt = build_system_prompt({}, schema={}, few_shot_example=few_shot)

        assert "INV-001" in prompt
        assert "expected_output" in prompt.lower()

    def test_user_prompt_includes_document_content(self):
        """Test that user prompt includes document content."""
        from app.services.llm.prompt_engine import build_user_prompt

        content = {
            "plain_text": "Invoice #001\nTotal: $100.00",
            "text_blocks": [
                {"block_id": "1.1.1:1:1", "text": "Invoice #001"},
                {"block_id": "1.1.2:1:1", "text": "Total: $100.00"},
            ],
        }

        prompt = build_user_prompt(content, document_name="invoice.pdf")

        assert "invoice.pdf" in prompt
        assert "Invoice #001" in prompt
        assert "1.1.1:1:1" in prompt

    def test_user_prompt_includes_text_blocks_with_ids(self):
        """Test that text blocks include their Block IDs."""
        from app.services.llm.prompt_engine import build_user_prompt

        content = {
            "plain_text": "Test content",
            "text_blocks": [
                {"block_id": "1.1.5:2:3", "text": "Block text"},
            ],
        }

        prompt = build_user_prompt(content, document_name="test.pdf")

        assert "1.1.5:2:3" in prompt
        assert "Block text" in prompt


# ====================
# 5.2 Source Mapping Protocol Tests
# ====================


class TestSourceMappingProtocol:
    """Tests for source mapping and Block ID validation."""

    def test_validate_block_id_pdf_format(self):
        """Test Block ID validation for PDF format."""
        from app.services.llm.validation import validate_block_id

        # Valid PDF Block IDs
        assert validate_block_id("1.1.5:2:3", document_type="pdf") is True
        assert validate_block_id("2.3.10:1:0", document_type="pdf") is True

        # Invalid formats
        assert validate_block_id("invalid", document_type="pdf") is False
        assert validate_block_id("1.1", document_type="pdf") is False

    def test_validate_block_id_excel_format(self):
        """Test Block ID validation for Excel format."""
        from app.services.llm.validation import validate_block_id

        # Valid Excel Block IDs
        assert validate_block_id("1.1.A1", document_type="excel") is True
        assert validate_block_id("1.2.B5:C10", document_type="excel") is True

        # Invalid formats
        assert validate_block_id("invalid", document_type="excel") is False

    def test_validate_extraction_result_block_ids(self):
        """Test validation of Block IDs in extraction result."""
        from app.services.llm.validation import validate_extraction_result

        result = {
            "invoice_number": {
                "value": "INV-001",
                "data_source": {"block_id": "1.1.1:1:1"},
            },
            "total": {
                "value": 100.00,
                "data_source": {"block_id": "1.1.2:2:1"},
            },
        }

        available_block_ids = {"1.1.1:1:1", "1.1.2:2:1", "1.1.3:1:1"}

        errors = validate_extraction_result(result, available_block_ids)
        assert len(errors) == 0

    def test_validate_extraction_result_missing_block_id(self):
        """Test validation catches missing Block IDs."""
        from app.services.llm.validation import validate_extraction_result

        result = {
            "invoice_number": {
                "value": "INV-001",
                "data_source": {"block_id": "1.1.99:99:99"},  # Does not exist
            },
        }

        available_block_ids = {"1.1.1:1:1", "1.1.2:2:1"}

        errors = validate_extraction_result(result, available_block_ids)
        assert len(errors) > 0
        assert any("1.1.99:99:99" in str(e) for e in errors)


# ====================
# 5.3 Structured Output Tests
# ====================


class TestStructuredOutput:
    """Tests for structured output parsing."""

    def test_parse_structured_output_valid(self):
        """Test parsing valid structured output."""
        from app.services.llm.structured_output import parse_extraction_result

        raw_output = {
            "invoice_number": {
                "value": "INV-001",
                "data_source": {"block_id": "1.1.1:1:1", "confidence": 0.95},
            },
        }

        result = parse_extraction_result(raw_output)

        assert result["invoice_number"]["value"] == "INV-001"
        assert result["invoice_number"]["data_source"]["block_id"] == "1.1.1:1:1"

    def test_parse_structured_output_handles_nested_objects(self):
        """Test parsing nested objects in output."""
        from app.services.llm.structured_output import parse_extraction_result

        raw_output = {
            "buyer": {
                "value": {
                    "name": "Company A",
                    "tax_id": "123456789",
                },
                "data_source": {"block_id": "1.1.1:1:1"},
            },
        }

        result = parse_extraction_result(raw_output)

        assert result["buyer"]["value"]["name"] == "Company A"

    def test_parse_structured_output_handles_arrays(self):
        """Test parsing array fields in output."""
        from app.services.llm.structured_output import parse_extraction_result

        raw_output = {
            "items": {
                "value": [
                    {"name": "Item 1", "price": 10.00},
                    {"name": "Item 2", "price": 20.00},
                ],
                "data_source": {"block_id": "1.1.5:1:1"},
            },
        }

        result = parse_extraction_result(raw_output)

        assert len(result["items"]["value"]) == 2


# ====================
# 5.4 Error Handling Tests
# ====================


class TestLLMErrorHandling:
    """Tests for LLM error handling."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
    async def test_handle_timeout_error(self):
        """Test handling LLM timeout."""
        from app.services.llm.executor import DigitizationExecutor

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=TimeoutError("Request timed out"))

        executor = DigitizationExecutor(llm_client=mock_llm)

        result = await executor.execute(
            content={"plain_text": "test", "text_blocks": []},
            schema={},
            config_id=1,
        )

        assert result["status"] == "error"
        assert any("timeout" in str(e).lower() for e in result.get("errors", []))

    @pytest.mark.asyncio
    async def test_handle_malformed_response(self):
        """Test handling malformed LLM response."""
        from app.services.llm.executor import DigitizationExecutor

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value="not valid json {{{")

        executor = DigitizationExecutor(llm_client=mock_llm)

        result = await executor.execute(
            content={"plain_text": "test", "text_blocks": []},
            schema={},
            config_id=1,
        )

        assert result["status"] == "error" or result["status"] == "review_required"

    @pytest.mark.asyncio
    async def test_preserve_raw_response_on_error(self):
        """Test that raw response is preserved for debugging."""
        from app.services.llm.executor import DigitizationExecutor

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value="malformed response")

        executor = DigitizationExecutor(llm_client=mock_llm)

        result = await executor.execute(
            content={"plain_text": "test", "text_blocks": []},
            schema={},
            config_id=1,
        )

        assert "raw_response" in result or result.get("status") == "error"


# ====================
# 5.5 Model Configuration Tests
# ====================


class TestModelConfiguration:
    """Tests for model configuration."""

    def test_apply_model_config_temperature(self):
        """Test that temperature is applied from config."""
        from app.services.llm.client_factory import build_model_kwargs

        model_config = {
            "model": "gpt-4o",
            "temperature": 0.0,
            "max_tokens": 4096,
        }

        kwargs = build_model_kwargs(model_config)

        assert kwargs["temperature"] == 0.0
        assert kwargs["max_tokens"] == 4096

    def test_apply_model_config_defaults(self):
        """Test that defaults are used for unspecified parameters."""
        from app.services.llm.client_factory import build_model_kwargs, DEFAULT_MODEL_CONFIG

        model_config = {"model": "gpt-4o"}

        kwargs = build_model_kwargs(model_config)

        assert kwargs["temperature"] == DEFAULT_MODEL_CONFIG["temperature"]

    @pytest.mark.skipif(not LANGCHAIN_OPENAI_AVAILABLE, reason="langchain-openai not installed")
    def test_create_langchain_client_openai(self):
        """Test creating LangChain client for OpenAI."""
        from app.services.llm.client_factory import create_llm_client

        with patch("langchain_openai.ChatOpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()

            config = {
                "provider": "openai",
                "model": "gpt-4o",
            }

            client = create_llm_client(config)

            mock_openai.assert_called_once()
            assert client is not None


# ====================
# 5.6 Digitization Executor Tests
# ====================


class TestDigitizationExecutor:
    """Tests for the main digitization executor."""

    @pytest.mark.asyncio
    async def test_execute_full_pipeline(self):
        """Test full extraction pipeline execution."""
        from app.services.llm.executor import DigitizationExecutor

        mock_llm = MagicMock()
        mock_result = {
            "invoice_number": {
                "value": "INV-001",
                "data_source": {"block_id": "1.1.1:1:1"},
            },
        }
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=str(mock_result)))
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)

        executor = DigitizationExecutor(llm_client=mock_llm)

        result = await executor.execute(
            content={
                "plain_text": "Invoice #INV-001",
                "text_blocks": [{"block_id": "1.1.1:1:1", "text": "INV-001"}],
            },
            schema={"properties": {"invoice_number": {"type": "string"}}},
            config_id=1,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_with_rag_examples(self):
        """Test extraction with RAG few-shot examples."""
        from app.services.llm.executor import DigitizationExecutor

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock())
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)

        mock_rag_service = AsyncMock()
        mock_rag_service.get_few_shot_examples = AsyncMock(
            return_value={
                "few_shot_examples": "<example>test</example>",
                "source": "rag",
            }
        )

        executor = DigitizationExecutor(
            llm_client=mock_llm,
            rag_service=mock_rag_service,
        )

        await executor.execute(
            content={"plain_text": "test", "text_blocks": []},
            schema={},
            config_id=1,
            rag_config={"enabled": True},
        )

        mock_rag_service.get_few_shot_examples.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_captures_langsmith_trace_id(self):
        """Test that LangSmith trace ID is captured."""
        from app.services.llm.executor import DigitizationExecutor

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock())
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)

        executor = DigitizationExecutor(llm_client=mock_llm)

        with patch("app.services.llm.executor.get_langsmith_run_id") as mock_trace:
            mock_trace.return_value = "trace-123"

            result = await executor.execute(
                content={"plain_text": "test", "text_blocks": []},
                schema={},
                config_id=1,
            )

            # Trace ID should be captured if available
            # Implementation may vary based on LangSmith setup

    @pytest.mark.asyncio
    async def test_execute_without_langsmith(self):
        """Test extraction works without LangSmith configured."""
        from app.services.llm.executor import DigitizationExecutor

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock())
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)

        executor = DigitizationExecutor(llm_client=mock_llm)

        # Should not raise error when LangSmith is not configured
        with patch.dict("os.environ", {"LANGSMITH_API_KEY": ""}):
            result = await executor.execute(
                content={"plain_text": "test", "text_blocks": []},
                schema={},
                config_id=1,
            )

            # Execution should complete without LangSmith
            assert result is not None


# ====================
# Integration Tests
# ====================


class TestLLMIntegration:
    """Integration tests for the LLM pipeline."""

    @pytest.mark.asyncio
    async def test_full_extraction_pipeline_with_validation(self):
        """Test full pipeline including prompt building and validation."""
        from app.services.llm.executor import DigitizationExecutor
        from app.services.llm.prompt_engine import build_system_prompt, build_user_prompt

        # Build prompts
        system_prompt = build_system_prompt(
            prompt_config={"task": "Extract invoice data"},
            schema={"properties": {"invoice_number": {"type": "string"}}},
        )

        content = {
            "plain_text": "Invoice #INV-001",
            "text_blocks": [{"block_id": "1.1.1:1:1", "text": "INV-001"}],
        }

        user_prompt = build_user_prompt(content, document_name="test.pdf")

        # Verify prompts are properly constructed
        assert "invoice" in system_prompt.lower()
        assert "INV-001" in user_prompt

        # Mock executor
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"invoice_number": {"value": "INV-001", "data_source": {"block_id": "1.1.1:1:1"}}}'
            )
        )
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)

        executor = DigitizationExecutor(llm_client=mock_llm)

        result = await executor.execute(
            content=content,
            schema={"properties": {"invoice_number": {"type": "string"}}},
            config_id=1,
        )

        assert result is not None
