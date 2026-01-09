"""Orchestrator for coordinating feedback loop operations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.feedback.audit_service import AuditService
from app.services.feedback.confirmation_service import ConfirmationService
from app.services.feedback.correction_service import CorrectionService
from app.services.feedback.training_service import TrainingDataService


class FeedbackOrchestrator:
    """Orchestrates correction, audit, confirmation, and training workflows."""

    def __init__(
        self,
        correction_service: CorrectionService,
        audit_service: AuditService,
        training_service: TrainingDataService,
        confirmation_service: ConfirmationService,
    ):
        """Initialize feedback orchestrator.

        Args:
            correction_service: Service for processing corrections.
            audit_service: Service for audit logging.
            training_service: Service for training data generation.
            confirmation_service: Service for result confirmation.
        """
        self.correction_service = correction_service
        self.audit_service = audit_service
        self.training_service = training_service
        self.confirmation_service = confirmation_service

    def _validate_correction(self, correction: Dict[str, Any]) -> None:
        """Validate correction payload before processing."""
        required_fields = ("field_path", "old_value", "new_value")
        missing = [field for field in required_fields if field not in correction]
        if missing:
            raise ValueError(f"Correction missing required fields: {missing}")

    async def process_correction_and_confirm(
        self,
        flow_id: int,
        result_id: int,
        correction: Dict[str, Any],
        content: Dict[str, Any],
        config_id: int,
    ) -> Dict[str, Any]:
        """Process a correction and optionally confirm and generate training data.

        This is the main workflow:
        1. Submit correction → new result version
        2. Log audit record
        3. Confirm the corrected result
        4. Generate training data from confirmed result

        Args:
            flow_id: Flow ID reference.
            result_id: Current result ID.
            correction: Correction details.
            content: Original document content.
            config_id: Configuration ID.

        Returns:
            Workflow result with confirmation and training status.
        """
        self._validate_correction(correction)
        # NOTE: If strict consistency is required, call this within a DB transaction.
        # Step 1: Submit correction
        correction_result = await self.correction_service.submit_correction(
            flow_id=flow_id,
            result_id=result_id,
            correction=correction,
        )

        # Step 2: Log audit record
        await self.audit_service.log_field_change(
            flow_id=flow_id,
            field_path=correction["field_path"],
            old_value=correction["old_value"],
            new_value=correction["new_value"],
            old_block_id=correction.get("old_block_id"),
            new_block_id=correction.get("block_id"),
            result_version=correction_result["version"],
        )

        # Step 3: Confirm the corrected result
        confirmed = await self.confirmation_service.confirm_result(
            flow_id=flow_id,
            result_id=result_id,
            confirmed_by="USER",
            notes="Manual correction applied",
        )

        # Step 4: Generate training data
        training_data = None
        training_generated = False
        if confirmed:
            extraction_result = correction_result.get("result", {}).get(
                "output_values", {}
            )
            training_data = await self.training_service.generate_training_data(
                flow_id=flow_id,
                config_id=config_id,
                content=content,
                extraction_result=extraction_result,
            )
            training_generated = training_data is not None

        return {
            "correction_version": correction_result["version"],
            "confirmed": confirmed,
            "training_data_generated": training_generated,
            "training_data_id": training_data.get("id") if training_data else None,
        }

    async def process_bulk_corrections_and_confirm(
        self,
        flow_id: int,
        result_id: int,
        corrections: List[Dict[str, Any]],
        content: Dict[str, Any],
        config_id: int,
    ) -> Dict[str, Any]:
        """Process multiple corrections atomically and confirm.

        Args:
            flow_id: Flow ID reference.
            result_id: Current result ID.
            corrections: List of correction details.
            content: Original document content.
            config_id: Configuration ID.

        Returns:
            Workflow result with confirmation and training status.
        """
        if not corrections:
            raise ValueError("At least one correction is required")
        for correction in corrections:
            self._validate_correction(correction)
        # NOTE: If strict consistency is required, call this within a DB transaction.
        # Step 1: Submit bulk corrections (single version)
        correction_result = await self.correction_service.submit_bulk_corrections(
            flow_id=flow_id,
            result_id=result_id,
            corrections=corrections,
        )

        # Step 2: Log audit records for each correction
        for correction in corrections:
            await self.audit_service.log_field_change(
                flow_id=flow_id,
                field_path=correction["field_path"],
                old_value=correction["old_value"],
                new_value=correction["new_value"],
                old_block_id=correction.get("old_block_id"),
                new_block_id=correction.get("block_id"),
                result_version=correction_result["version"],
            )

        # Step 3: Confirm
        confirmed = await self.confirmation_service.confirm_result(
            flow_id=flow_id,
            result_id=result_id,
            confirmed_by="USER",
            notes=f"Bulk correction: {len(corrections)} fields",
        )

        # Step 4: Generate training data
        training_data = None
        training_generated = False
        if confirmed:
            extraction_result = correction_result.get("result", {}).get(
                "output_values", {}
            )
            training_data = await self.training_service.generate_training_data(
                flow_id=flow_id,
                config_id=config_id,
                content=content,
                extraction_result=extraction_result,
            )
            training_generated = training_data is not None

        return {
            "correction_version": correction_result["version"],
            "corrections_applied": len(corrections),
            "confirmed": confirmed,
            "training_data_generated": training_generated,
        }

    async def auto_confirm_if_eligible(
        self,
        flow_id: int,
        result_id: int,
        extraction_result: Dict[str, Any],
        validation_result: Dict[str, Any],
        content: Dict[str, Any],
        config_id: int,
        confidence_threshold: float = 0.9,
    ) -> Dict[str, Any]:
        """Attempt auto-confirmation based on confidence.

        Args:
            flow_id: Flow ID reference.
            result_id: Result ID.
            extraction_result: The extraction result.
            validation_result: Validation result.
            content: Original document content.
            config_id: Configuration ID.
            confidence_threshold: Minimum confidence for auto-confirm.

        Returns:
            Result with confirmation status and training data generation.
        """
        # Check if eligible for auto-confirmation
        should_auto = self.confirmation_service.should_auto_confirm(
            extraction_result=extraction_result,
            validation_result=validation_result,
            threshold=confidence_threshold,
        )

        if not should_auto:
            return {
                "auto_confirmed": False,
                "reason": "Below confidence threshold or validation errors",
                "training_data_generated": False,
            }

        # Auto-confirm
        confirmed = await self.confirmation_service.confirm_result(
            flow_id=flow_id,
            result_id=result_id,
            confirmed_by="AUTO",
            notes=f"Auto-confirmed with threshold {confidence_threshold}",
        )

        # Generate training data
        training_data = None
        training_generated = False
        if confirmed:
            training_data = await self.training_service.generate_training_data(
                flow_id=flow_id,
                config_id=config_id,
                content=content,
                extraction_result=extraction_result,
            )
            training_generated = training_data is not None

        return {
            "auto_confirmed": True,
            "training_data_generated": training_generated,
            "training_data_id": training_data.get("id") if training_data else None,
        }
