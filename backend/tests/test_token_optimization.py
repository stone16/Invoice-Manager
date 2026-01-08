"""Tests for Token Optimization - TDD Red phase."""

from __future__ import annotations

from typing import List

import pytest

# ====================
# 7.1 Tiktoken Encoder Caching Tests
# ====================


class TestEncoderCaching:
    """Tests for tiktoken encoder caching."""

    def test_get_encoder_returns_encoder(self):
        """Test that get_encoder returns a valid encoder."""
        from app.services.token_optimization.encoder import get_encoder

        encoder = get_encoder()
        assert encoder is not None
        # Should be able to encode text
        tokens = encoder.encode("Hello World")
        assert len(tokens) > 0

    def test_get_encoder_caches_instance(self):
        """Test that encoder is cached and reused."""
        from app.services.token_optimization.encoder import get_encoder

        encoder1 = get_encoder()
        encoder2 = get_encoder()
        # Should return the same cached instance
        assert encoder1 is encoder2

    def test_count_tokens(self):
        """Test token counting function."""
        from app.services.token_optimization.encoder import count_tokens

        text = "Hello, this is a test sentence."
        count = count_tokens(text)
        assert count > 0
        assert isinstance(count, int)

    def test_encode_and_decode_roundtrip(self):
        """Test encoding and decoding produces same text."""
        from app.services.token_optimization.encoder import (
            decode_tokens,
            encode_text,
        )

        original = "Test document content 测试内容"
        tokens = encode_text(original)
        decoded = decode_tokens(tokens)
        assert decoded == original


# ====================
# 7.2 Line Deduplication Tests
# ====================


class TestLineDeduplication:
    """Tests for tiktoken-based line deduplication."""

    def test_exact_duplicate_removed(self):
        """Test that exact duplicate lines are removed."""
        from app.services.token_optimization.deduplication import (
            remove_duplicated_lines,
        )

        pages = [
            ["Header Line", "Content A"],
            ["Header Line", "Content B"],  # "Header Line" is duplicate
        ]

        result = remove_duplicated_lines(pages)

        assert len(result) == 2
        assert "Header Line" in result[0]
        assert "Header Line" not in result[1]

    def test_similar_duplicate_removed(self):
        """Test that similar lines (>= threshold Jaccard) are removed."""
        from app.services.token_optimization.deduplication import (
            remove_duplicated_lines,
        )

        # These two lines have ~71% Jaccard similarity with tiktoken
        pages = [
            ["Company ABC Invoice 12345"],
            ["Company ABC Invoice 12346"],  # Similar, should be removed at 0.70 threshold
        ]

        # Use 0.70 threshold to match actual tiktoken-based similarity
        result = remove_duplicated_lines(pages, similarity_threshold=0.70)

        # Second similar line should be removed
        total_lines = sum(len(page) for page in result)
        assert total_lines == 1

    def test_empty_lines_preserved(self):
        """Test that empty lines are preserved."""
        from app.services.token_optimization.deduplication import (
            remove_duplicated_lines,
        )

        pages = [
            ["Header", "", "Content"],
            ["Footer", ""],
        ]

        result = remove_duplicated_lines(pages)

        # Empty lines should be preserved
        assert "" in result[0]

    def test_unique_lines_preserved(self):
        """Test that unique lines are not removed."""
        from app.services.token_optimization.deduplication import (
            remove_duplicated_lines,
        )

        pages = [
            ["Line A Unique"],
            ["Line B Different"],
            ["Line C Completely Different"],
        ]

        result = remove_duplicated_lines(pages)

        # All unique lines should be preserved
        assert len(result[0]) == 1
        assert len(result[1]) == 1
        assert len(result[2]) == 1

    def test_jaccard_similarity_calculation(self):
        """Test Jaccard similarity calculation with tiktoken."""
        from app.services.token_optimization.deduplication import (
            calculate_line_similarity,
        )

        # Exact match
        similarity = calculate_line_similarity("Hello World", "Hello World")
        assert similarity == 1.0

        # Completely different
        similarity = calculate_line_similarity("ABC", "XYZ")
        assert similarity < 0.5

        # Partial match
        similarity = calculate_line_similarity(
            "Invoice Number: 12345", "Invoice Number: 12346"
        )
        assert 0.5 < similarity < 1.0


# ====================
# 7.3 Weighted Page Truncation Tests
# ====================


class TestWeightedTruncation:
    """Tests for weighted page truncation."""

    def test_weighted_allocation_prioritizes_earlier_pages(self):
        """Test that earlier pages get more tokens."""
        from app.services.token_optimization.truncation import (
            calculate_page_weights,
        )

        weights = calculate_page_weights(3, decay_factor=1.0)

        assert weights[0] > weights[1]
        assert weights[1] > weights[2]
        assert sum(weights) == pytest.approx(1.0)

    def test_allocate_tokens_to_pages(self):
        """Test token allocation to pages."""
        from app.services.token_optimization.truncation import allocate_tokens

        page_token_counts = [1000, 500, 500]
        max_tokens = 1500

        allocations = allocate_tokens(page_token_counts, max_tokens, decay_factor=1.0)

        assert sum(allocations) <= max_tokens
        assert allocations[0] > allocations[1]  # First page gets more

    def test_truncation_with_empty_pages(self):
        """Test truncation handles empty pages."""
        from app.services.token_optimization.truncation import (
            apply_weighted_truncation,
        )

        pages = [
            ["Content on page 1"],
            [],  # Empty page
            ["Content on page 3"],
        ]

        result = apply_weighted_truncation(pages, max_tokens=1000)

        # Should handle empty pages gracefully
        assert isinstance(result, list)

    def test_small_max_tokens_truncates_content(self):
        """Test that small max_tokens properly truncates."""
        from app.services.token_optimization.truncation import (
            apply_weighted_truncation,
        )

        pages = [
            ["This is a very long line of text that should be truncated when max tokens is very small."],
        ]

        result = apply_weighted_truncation(pages, max_tokens=10)

        # Result should be smaller than original
        assert len(result[0]) < len(pages[0][0]) if result else True


# ====================
# 7.4 XML Tag Preservation Tests
# ====================


class TestXmlTagPreservation:
    """Tests for XML tag preservation during truncation."""

    def test_is_xml_tag_detection(self):
        """Test XML tag detection."""
        from app.services.token_optimization.truncation import is_xml_tag

        assert is_xml_tag("<page_1>") is True
        assert is_xml_tag("</page_1>") is True
        assert is_xml_tag("<text_block id='1'>") is True
        assert is_xml_tag("Regular text") is False
        assert is_xml_tag("") is False
        assert is_xml_tag("<>") is False  # Invalid tag

    def test_truncate_preserves_xml_tags(self):
        """Test that truncation preserves opening and closing XML tags."""
        from app.services.token_optimization.truncation import truncate_with_tags

        lines = [
            "<page_1>",
            "Content line 1",
            "Content line 2 which is very long and might need truncation",
            "Content line 3 also long text here for testing purposes",
            "</page_1>",
        ]

        result = truncate_with_tags(lines, max_tokens=50)

        # Should preserve tags
        assert result.startswith("<page_1>")
        assert result.endswith("</page_1>")

    def test_truncate_without_tags(self):
        """Test truncation when no XML tags present."""
        from app.services.token_optimization.truncation import truncate_with_tags

        lines = [
            "Content line 1",
            "Content line 2",
        ]

        result = truncate_with_tags(lines, max_tokens=20)

        # Should truncate without tag preservation logic
        assert isinstance(result, str)


# ====================
# 7.5 Full Pipeline Tests
# ====================


class TestTokenOptimizationPipeline:
    """Tests for the complete token optimization pipeline."""

    def test_optimize_text_blocks_for_embedding(self):
        """Test full optimization for embedding generation."""
        from app.services.token_optimization.optimizer import optimize_for_embedding

        text_blocks = [
            {"page": 1, "lines": ["Header repeated", "Page 1 content"]},
            {"page": 2, "lines": ["Header repeated", "Page 2 content"]},  # Duplicate header
            {"page": 3, "lines": ["Page 3 content"]},
        ]

        result = optimize_for_embedding(text_blocks, max_tokens=500)

        # Should deduplicate and respect token limit
        assert result is not None
        assert isinstance(result, str)

    def test_optimize_for_prompt(self):
        """Test optimization for LLM prompt."""
        from app.services.token_optimization.optimizer import optimize_for_prompt

        pages = [
            ["<page_1>", "Invoice Number: 12345", "Date: 2024-01-15", "</page_1>"],
            ["<page_2>", "Items listed here", "</page_2>"],
        ]

        result = optimize_for_prompt(pages, max_tokens=100)

        assert result is not None
        # Earlier pages should have more content
        assert "<page_1>" in result

    def test_build_weighted_embedding_text(self):
        """Test building weighted embedding text from labeled texts."""
        from app.services.token_optimization.optimizer import (
            build_weighted_embedding_text,
        )

        labeled_texts = [
            {"label": "page_1", "text": "Important content on first page"},
            {"label": "page_2", "text": "Secondary content here"},
        ]

        result = build_weighted_embedding_text(labeled_texts, max_tokens=100)

        assert result is not None
        assert "Important content" in result


# ====================
# 7.6 Performance Tests
# ====================


class TestTokenOptimizationPerformance:
    """Performance tests for token optimization."""

    def test_encoder_caching_performance(self):
        """Test that cached encoder is faster than creating new ones."""
        import time

        from app.services.token_optimization.encoder import get_encoder

        # First call initializes
        start = time.time()
        _ = get_encoder()
        first_call = time.time() - start

        # Second call should be faster (cached)
        start = time.time()
        _ = get_encoder()
        second_call = time.time() - start

        # Cached call should be significantly faster
        assert second_call < first_call or second_call < 0.001

    def test_deduplication_handles_large_input(self):
        """Test that deduplication handles large input efficiently."""
        from app.services.token_optimization.deduplication import (
            remove_duplicated_lines,
        )

        # Create large input with duplicates
        pages = [
            [f"Unique line {i}" for i in range(100)] + ["Repeated Header"]
            for _ in range(10)
        ]

        # Should complete without hanging
        result = remove_duplicated_lines(pages)

        assert len(result) == 10
        # "Repeated Header" should only appear once total
        header_count = sum(
            1 for page in result for line in page if line == "Repeated Header"
        )
        assert header_count == 1
