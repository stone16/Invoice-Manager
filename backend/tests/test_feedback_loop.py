"""Tests for Feedback Loop - TDD Red phase."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


# ====================
# 6.1 Correction Processing Tests
# ====================


class TestCorrectionProcessing:
    """Tests for processing human corrections."""

    @pytest.mark.asyncio
    async def test_submit_field_correction_creates_new_version(self):
        """Test that field correction creates a new result version."""
        from app.services.feedback.correction_service import CorrectionService

        mock_db = AsyncMock()
        service = CorrectionService(db=mock_db)

        correction = {
            "field_path": "invoice_number.value",
            "old_value": "INV-001",
            "new_value": "INV-002",
            "block_id": "1.1.1:1:1",
        }

        result = await service.submit_correction(
            flow_id=1,
            result_id=1,
            correction=correction,
        )

        assert result is not None
        assert result["version"] > 1
        assert result["data_origin"] == "USER"

    @pytest.mark.asyncio
    async def test_submit_bulk_corrections_atomically(self):
        """Test that bulk corrections are applied atomically."""
        from app.services.feedback.correction_service import CorrectionService

        mock_db = AsyncMock()
        service = CorrectionService(db=mock_db)

        corrections = [
            {
                "field_path": "invoice_number.value",
                "old_value": "INV-001",
                "new_value": "INV-002",
                "block_id": "1.1.1:1:1",
            },
            {
                "field_path": "total_amount.value",
                "old_value": 100.00,
                "new_value": 150.00,
                "block_id": "1.1.2:1:1",
            },
        ]

        result = await service.submit_bulk_corrections(
            flow_id=1,
            result_id=1,
            corrections=corrections,
        )

        # Single version created for all corrections
        assert result["version"] > 1
        assert len(result.get("applied_corrections", [])) == 2

    @pytest.mark.asyncio
    async def test_correction_preserves_original_result(self):
        """Test that original result is preserved after correction."""
        from app.services.feedback.correction_service import CorrectionService

        mock_db = AsyncMock()
        service = CorrectionService(db=mock_db)

        correction = {
            "field_path": "invoice_number.value",
            "old_value": "INV-001",
            "new_value": "INV-002",
            "block_id": "1.1.1:1:1",
        }

        await service.submit_correction(
            flow_id=1,
            result_id=1,
            correction=correction,
        )

        # Original should still be accessible
        original = await service.get_result_version(flow_id=1, result_id=1, version=1)
        assert original is not None


# ====================
# 6.2 Field Audit Logging Tests
# ====================


class TestFieldAuditLogging:
    """Tests for field-level audit logging."""

    @pytest.mark.asyncio
    async def test_log_field_correction_creates_audit_record(self):
        """Test that field correction creates audit record."""
        from app.services.feedback.audit_service import AuditService

        mock_db = AsyncMock()
        service = AuditService(db=mock_db)

        audit_entry = {
            "flow_id": 1,
            "field_path": "invoice_number.value",
            "old_value": "INV-001",
            "new_value": "INV-002",
            "old_block_id": "1.1.1:1:1",
            "new_block_id": "1.1.2:1:1",
        }

        result = await service.log_field_change(**audit_entry)

        assert result is not None
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_query_field_audit_history_returns_chronologically(self):
        """Test that audit history is returned chronologically."""
        from app.services.feedback.audit_service import AuditService

        mock_db = AsyncMock()
        service = AuditService(db=mock_db)

        # Mock returning multiple audit records
        mock_records = [
            MagicMock(created_at="2024-01-01T10:00:00"),
            MagicMock(created_at="2024-01-01T11:00:00"),
            MagicMock(created_at="2024-01-01T12:00:00"),
        ]
        # Create a proper mock result object that returns sync values
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_records
        mock_db.execute.return_value = mock_result

        history = await service.get_audit_history(flow_id=1)

        assert len(history) == 3
        # Should be chronological (oldest first)
        assert history[0].created_at < history[-1].created_at


# ====================
# 6.3 Training Data Generation Tests
# ====================


class TestTrainingDataGeneration:
    """Tests for RAG training data generation."""

    @pytest.mark.asyncio
    async def test_generate_training_vector_on_confirmation(self):
        """Test training vector generation on confirmation."""
        from app.services.feedback.training_service import TrainingDataService

        mock_db = AsyncMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.generate_embedding.return_value = [0.1] * 1536

        service = TrainingDataService(
            db=mock_db,
            embedding_service=mock_embedding_service,
        )

        extraction_result = {
            "invoice_number": {
                "value": "INV-001",
                "data_source": {"block_id": "1.1.1:1:1"},
            },
        }

        content = {
            "plain_text": "Invoice INV-001",
            "text_blocks": [{"block_id": "1.1.1:1:1", "text": "INV-001"}],
        }

        result = await service.generate_training_data(
            flow_id=1,
            config_id=1,
            content=content,
            extraction_result=extraction_result,
        )

        assert result is not None
        mock_embedding_service.generate_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_content_selection_includes_referenced_blocks(self):
        """Test that only referenced blocks are included in training."""
        from app.services.feedback.training_service import TrainingDataService

        mock_db = AsyncMock()
        service = TrainingDataService(db=mock_db)

        all_blocks = [
            {"block_id": "1.1.1:1:1", "text": "INV-001"},
            {"block_id": "1.1.2:1:1", "text": "Unreferenced"},
            {"block_id": "1.1.3:1:1", "text": "2024-01-15"},
        ]

        extraction_result = {
            "invoice_number": {
                "value": "INV-001",
                "data_source": {"block_id": "1.1.1:1:1"},
            },
            "date": {
                "value": "2024-01-15",
                "data_source": {"block_id": "1.1.3:1:1"},
            },
        }

        selected = service.select_partial_content(
            all_blocks, extraction_result, context_window=0
        )

        block_ids = [b["block_id"] for b in selected]
        assert "1.1.1:1:1" in block_ids
        assert "1.1.3:1:1" in block_ids
        assert "1.1.2:1:1" not in block_ids


# ====================
# 6.4 Automatic Confirmation Tests
# ====================


class TestAutomaticConfirmation:
    """Tests for automatic confirmation based on confidence."""

    @pytest.mark.asyncio
    async def test_high_confidence_auto_confirmation(self):
        """Test that high-confidence results are auto-confirmed."""
        from app.services.feedback.confirmation_service import ConfirmationService

        mock_db = AsyncMock()
        service = ConfirmationService(db=mock_db)

        extraction_result = {
            "invoice_number": {
                "value": "INV-001",
                "data_source": {"block_id": "1.1.1:1:1", "confidence": 0.95},
            },
            "total": {
                "value": 100.00,
                "data_source": {"block_id": "1.1.2:1:1", "confidence": 0.98},
            },
        }

        validation_result = {
            "errors": [],
            "warnings": [],
        }

        should_auto = service.should_auto_confirm(
            extraction_result=extraction_result,
            validation_result=validation_result,
            threshold=0.9,
        )

        assert should_auto is True

    @pytest.mark.asyncio
    async def test_low_confidence_requires_manual_review(self):
        """Test that low-confidence results require manual review."""
        from app.services.feedback.confirmation_service import ConfirmationService

        mock_db = AsyncMock()
        service = ConfirmationService(db=mock_db)

        extraction_result = {
            "invoice_number": {
                "value": "INV-001",
                "data_source": {"block_id": "1.1.1:1:1", "confidence": 0.5},
            },
        }

        validation_result = {
            "errors": [],
            "warnings": ["Low confidence extraction"],
        }

        should_auto = service.should_auto_confirm(
            extraction_result=extraction_result,
            validation_result=validation_result,
            threshold=0.9,
        )

        assert should_auto is False

    @pytest.mark.asyncio
    async def test_validation_errors_require_manual_review(self):
        """Test that validation errors require manual review."""
        from app.services.feedback.confirmation_service import ConfirmationService

        mock_db = AsyncMock()
        service = ConfirmationService(db=mock_db)

        extraction_result = {
            "invoice_number": {
                "value": "INV-001",
                "data_source": {"block_id": "invalid", "confidence": 0.99},
            },
        }

        validation_result = {
            "errors": ["Invalid block_id format"],
            "warnings": [],
        }

        should_auto = service.should_auto_confirm(
            extraction_result=extraction_result,
            validation_result=validation_result,
            threshold=0.9,
        )

        assert should_auto is False


# ====================
# 6.5 Training Data Quality Tests
# ====================


class TestTrainingDataQuality:
    """Tests for training data quality validation."""

    def test_validate_training_data_non_empty_input(self):
        """Test that training data requires non-empty input."""
        from app.services.feedback.training_service import validate_training_data

        training_data = {
            "reference_input": {},  # Empty
            "reference_output": {"field": {"value": "test"}},
            "embedding": [0.1] * 1536,
        }

        errors = validate_training_data(training_data)

        assert len(errors) > 0
        assert any("input" in e.lower() for e in errors)

    def test_validate_training_data_valid_embedding_dimensions(self):
        """Test that embedding must be 1536 dimensions."""
        from app.services.feedback.training_service import validate_training_data

        training_data = {
            "reference_input": {"plain_text": "test", "text_blocks": []},
            "reference_output": {"field": {"value": "test"}},
            "embedding": [0.1] * 100,  # Wrong dimensions
        }

        errors = validate_training_data(training_data)

        assert len(errors) > 0
        assert any("1536" in e or "dimension" in e.lower() for e in errors)

    def test_validate_training_data_block_ids_exist(self):
        """Test that all block_ids in output exist in input."""
        from app.services.feedback.training_service import validate_training_data

        training_data = {
            "reference_input": {
                "plain_text": "test",
                "text_blocks": [{"block_id": "1.1.1:1:1", "text": "test"}],
            },
            "reference_output": {
                "field": {
                    "value": "test",
                    "data_source": {"block_id": "9.9.9:9:9"},  # Not in input
                }
            },
            "embedding": [0.1] * 1536,
        }

        errors = validate_training_data(training_data)

        assert len(errors) > 0
        assert any("block_id" in e.lower() for e in errors)

    def test_exclude_low_quality_training_data(self):
        """Test that low-quality data is excluded."""
        from app.services.feedback.training_service import should_generate_training

        extraction_result = {
            "field1": {"value": None},
            "field2": {"value": None},
            "field3": {"value": None},
        }

        should_generate = should_generate_training(
            extraction_result=extraction_result,
            min_populated_ratio=0.5,
        )

        assert should_generate is False


# ====================
# 6.6 Feedback Statistics Tests
# ====================


class TestFeedbackStatistics:
    """Tests for feedback statistics tracking."""

    @pytest.mark.asyncio
    async def test_track_correction_rate(self):
        """Test tracking correction rate per config."""
        from app.services.feedback.statistics_service import StatisticsService

        mock_db = AsyncMock()
        service = StatisticsService(db=mock_db)

        # Mock statistics query with proper MagicMock result
        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(
            total_extractions=100,
            auto_confirmed=70,
            manual_corrections=30,
        )
        mock_db.execute.return_value = mock_result

        stats = await service.get_config_statistics(config_id=1)

        assert stats["total_extractions"] == 100
        assert stats["auto_confirmed_count"] == 70
        assert stats["manual_correction_count"] == 30
        assert stats["correction_rate"] == 0.3

    @pytest.mark.asyncio
    async def test_identify_problematic_fields(self):
        """Test identifying fields with high correction rate."""
        from app.services.feedback.statistics_service import StatisticsService

        mock_db = AsyncMock()
        service = StatisticsService(db=mock_db)

        # Mock field statistics with proper MagicMock result
        field_stats = [
            MagicMock(field_path="invoice_number", corrections=5, total=100),
            MagicMock(field_path="tax_id", corrections=45, total=100),  # >30%
            MagicMock(field_path="total", corrections=35, total=100),  # >30%
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = field_stats
        mock_db.execute.return_value = mock_result

        problematic = await service.get_problematic_fields(
            config_id=1, threshold=0.3
        )

        assert len(problematic) == 2
        assert any(f["field_path"] == "tax_id" for f in problematic)
        assert any(f["field_path"] == "total" for f in problematic)


# ====================
# 6.7 Training Data Lifecycle Tests
# ====================


class TestTrainingDataLifecycle:
    """Tests for training data lifecycle management."""

    @pytest.mark.asyncio
    async def test_update_training_data_on_reconfirmation(self):
        """Test that training data is updated on re-confirmation."""
        from app.services.feedback.training_service import TrainingDataService

        mock_db = AsyncMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.generate_embedding.return_value = [0.2] * 1536

        service = TrainingDataService(
            db=mock_db,
            embedding_service=mock_embedding_service,
        )

        # Mock existing training data with proper MagicMock result
        existing_training = MagicMock(id=1, embedding=[0.1] * 1536)
        mock_result = MagicMock()
        mock_result.scalar.return_value = existing_training
        mock_db.execute.return_value = mock_result

        # New extraction result after correction
        extraction_result = {
            "invoice_number": {
                "value": "INV-002",  # Corrected
                "data_source": {"block_id": "1.1.1:1:1"},
            },
        }

        content = {
            "plain_text": "Invoice INV-002",
            "text_blocks": [{"block_id": "1.1.1:1:1", "text": "INV-002"}],
        }

        result = await service.update_training_data(
            flow_id=1,
            config_id=1,
            content=content,
            extraction_result=extraction_result,
        )

        # Should update existing, not create new
        assert result is not None

    @pytest.mark.asyncio
    async def test_training_data_deleted_with_flow(self):
        """Test that training data is deleted when flow is deleted."""
        from app.services.feedback.training_service import TrainingDataService

        mock_db = AsyncMock()
        service = TrainingDataService(db=mock_db)

        await service.delete_training_data(flow_id=1)

        mock_db.execute.assert_called()


# ====================
# Integration Tests
# ====================


class TestFeedbackLoopIntegration:
    """Integration tests for the feedback loop."""

    @pytest.mark.asyncio
    async def test_full_correction_workflow(self):
        """Test complete correction → audit → training workflow."""
        from app.services.feedback.feedback_orchestrator import FeedbackOrchestrator

        mock_correction_service = AsyncMock()
        mock_audit_service = AsyncMock()
        mock_training_service = AsyncMock()
        mock_confirmation_service = AsyncMock()

        mock_correction_service.submit_correction.return_value = {
            "version": 2,
            "data_origin": "USER",
        }
        mock_confirmation_service.confirm_result.return_value = True
        mock_training_service.generate_training_data.return_value = {"id": 1}

        orchestrator = FeedbackOrchestrator(
            correction_service=mock_correction_service,
            audit_service=mock_audit_service,
            training_service=mock_training_service,
            confirmation_service=mock_confirmation_service,
        )

        result = await orchestrator.process_correction_and_confirm(
            flow_id=1,
            result_id=1,
            correction={
                "field_path": "invoice_number.value",
                "old_value": "INV-001",
                "new_value": "INV-002",
                "block_id": "1.1.1:1:1",
            },
            content={"plain_text": "test", "text_blocks": []},
            config_id=1,
        )

        # All services should be called
        mock_correction_service.submit_correction.assert_called_once()
        mock_audit_service.log_field_change.assert_called_once()
        mock_confirmation_service.confirm_result.assert_called_once()
        mock_training_service.generate_training_data.assert_called_once()

        assert result["confirmed"] is True
        assert result["training_data_generated"] is True
