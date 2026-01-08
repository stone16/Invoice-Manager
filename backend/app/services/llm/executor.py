"""Digitization executor for orchestrating LLM-based extraction."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.services.llm.prompt_engine import build_system_prompt, build_user_prompt
from app.services.llm.structured_output import (
    build_extraction_response,
    parse_extraction_result,
)
from app.services.llm.validation import (
    extract_block_ids_from_result,
    validate_extraction_result,
)


def get_langsmith_run_id() -> Optional[str]:
    """Get the current LangSmith run ID if available.

    Returns:
        Run ID string or None if not available.
    """
    try:
        from langsmith import get_current_run_tree

        run_tree = get_current_run_tree()
        if run_tree:
            return str(run_tree.id)
    except (ImportError, Exception):
        pass
    return None


class DigitizationExecutor:
    """Orchestrates document digitization using LLM."""

    def __init__(
        self,
        llm_client: Any,
        rag_service: Optional[Any] = None,
    ):
        """Initialize the executor.

        Args:
            llm_client: LangChain chat model client.
            rag_service: Optional RAG service for few-shot examples.
        """
        self.llm_client = llm_client
        self.rag_service = rag_service

    async def execute(
        self,
        content: Dict[str, Any],
        schema: Dict[str, Any],
        config_id: int,
        prompt_config: Optional[Dict[str, Any]] = None,
        rag_config: Optional[Dict[str, Any]] = None,
        document_name: str = "document",
        document_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute digitization on document content.

        Args:
            content: Document content with plain_text and text_blocks.
            schema: JSON schema for extraction output.
            config_id: Configuration ID for RAG filtering.
            prompt_config: Optional prompt configuration.
            rag_config: Optional RAG configuration.
            document_name: Name of the document.
            document_type: Optional document type for block-id validation.

        Returns:
            Extraction result dictionary with status, data, and metadata.
        """
        if prompt_config is None:
            prompt_config = {}

        try:
            # Get few-shot examples if RAG is enabled
            few_shot_example = None
            if self.rag_service and rag_config and rag_config.get("enabled"):
                rag_result = await self.rag_service.get_few_shot_examples(
                    content=content.get("plain_text", ""),
                    config_id=config_id,
                    rag_config=rag_config,
                    schema=schema,
                )
                few_shot_example = rag_result.get("few_shot_examples")

            # Build prompts
            system_prompt = build_system_prompt(
                prompt_config=prompt_config,
                schema=schema,
                few_shot_example=few_shot_example,
            )

            user_prompt = build_user_prompt(
                content=content,
                document_name=document_name,
            )

            # Execute LLM call
            raw_response = await self._invoke_llm(system_prompt, user_prompt, schema)

            # Parse response
            parsed_result = self._parse_response(raw_response)

            # Validate block IDs
            available_block_ids = self._extract_available_block_ids(content)
            validation_errors = validate_extraction_result(
                parsed_result,
                available_block_ids,
                document_type=self._resolve_document_type(content, document_type),
            )

            # Determine status
            if validation_errors:
                status = "review_required"
            else:
                status = "success"

            # Capture trace ID
            trace_id = get_langsmith_run_id()

            return build_extraction_response(
                extracted_data=parsed_result,
                status=status,
                errors=validation_errors if validation_errors else None,
                trace_id=trace_id,
            )

        except TimeoutError as e:
            return build_extraction_response(
                extracted_data={},
                status="error",
                errors=[f"Timeout error: {str(e)}"],
            )
        except Exception as e:
            return build_extraction_response(
                extracted_data={},
                status="error",
                errors=[str(e)],
                raw_response=str(e),
            )

    async def _invoke_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
    ) -> Any:
        """Invoke the LLM with prompts.

        Args:
            system_prompt: System prompt string.
            user_prompt: User prompt string.
            schema: Output schema for structured output.

        Returns:
            LLM response.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # Try to use structured output if available
        try:
            if hasattr(self.llm_client, "with_structured_output") and schema:
                structured_llm = self.llm_client.with_structured_output(schema)
                response = await structured_llm.ainvoke(messages)
                return response
        except Exception:
            pass

        # Fall back to regular invocation
        response = await self.llm_client.ainvoke(messages)
        return response

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse LLM response to extraction result.

        Args:
            response: Raw LLM response.

        Returns:
            Parsed extraction result.
        """
        # Handle different response types
        if isinstance(response, dict):
            return parse_extraction_result(response)

        if hasattr(response, "content"):
            content = response.content
            if isinstance(content, dict):
                return parse_extraction_result(content)
            return parse_extraction_result(str(content))

        if isinstance(response, str):
            return parse_extraction_result(response)

        # Try to convert to dict
        try:
            return parse_extraction_result(dict(response))
        except Exception as e:
            raise ValueError(f"Could not parse response: {type(response)}") from e

    def _extract_available_block_ids(
        self,
        content: Dict[str, Any],
    ) -> set:
        """Extract available block IDs from document content.

        Args:
            content: Document content with text_blocks.

        Returns:
            Set of available block IDs.
        """
        block_ids = set()
        text_blocks = content.get("text_blocks", [])

        for block in text_blocks:
            block_id = block.get("block_id")
            if block_id:
                block_ids.add(block_id)

        return block_ids

    def _resolve_document_type(
        self,
        content: Dict[str, Any],
        override: Optional[str],
    ) -> str:
        """Resolve document type for block ID validation."""
        if override:
            return override

        doc_type = content.get("document_type")
        if isinstance(doc_type, str) and doc_type:
            return doc_type

        content_type = content.get("content_type") or content.get("file_type")
        if isinstance(content_type, str):
            lowered = content_type.lower()
            if lowered in {"pdf", "excel", "image"}:
                return "pdf" if lowered == "image" else lowered
        if isinstance(content_type, int):
            if content_type == 2:
                return "excel"
            if content_type in {1, 3}:
                return "pdf"

        file_name = content.get("file_name", "")
        if isinstance(file_name, str) and "." in file_name:
            ext = file_name.rsplit(".", 1)[-1].lower()
            if ext in {"xlsx", "xls"}:
                return "excel"
            if ext in {"png", "jpg", "jpeg", "bmp", "tiff"}:
                return "pdf"

        return "pdf"


class BatchDigitizationExecutor:
    """Handles batch digitization of multiple documents."""

    def __init__(
        self,
        executor: DigitizationExecutor,
        max_concurrent: int = 5,
    ):
        """Initialize batch executor.

        Args:
            executor: Single document executor.
            max_concurrent: Maximum concurrent executions.
        """
        self.executor = executor
        self.max_concurrent = max_concurrent

    async def execute_batch(
        self,
        documents: List[Dict[str, Any]],
        schema: Dict[str, Any],
        config_id: int,
        prompt_config: Optional[Dict[str, Any]] = None,
        rag_config: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute digitization on multiple documents.

        Args:
            documents: List of document content dicts.
            schema: JSON schema for extraction.
            config_id: Configuration ID.
            prompt_config: Optional prompt configuration.
            rag_config: Optional RAG configuration.

        Returns:
            List of extraction results.
        """
        import asyncio

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def process_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await self.executor.execute(
                    content=doc.get("content", {}),
                    schema=schema,
                    config_id=config_id,
                    prompt_config=prompt_config,
                    rag_config=rag_config,
                    document_name=doc.get("name", "document"),
                )

        tasks = [process_doc(doc) for doc in documents]
        return await asyncio.gather(*tasks)
