"""Service for handling result confirmation based on confidence."""

from __future__ import annotations

from typing import Any, Dict, Optional


class ConfirmationService:
    """Service for managing result confirmation."""

    def __init__(self, db: Any):
        """Initialize confirmation service.

        Args:
            db: Database session.
        """
        self.db = db

    def should_auto_confirm(
        self,
        extraction_result: Dict[str, Any],
        validation_result: Dict[str, Any],
        threshold: float = 0.9,
    ) -> bool:
        """Determine if result should be auto-confirmed.

        Auto-confirmation requires:
        1. No validation errors
        2. All field confidences above threshold

        Args:
            extraction_result: The extraction result to evaluate.
            validation_result: Validation result with errors/warnings.
            threshold: Minimum confidence threshold.

        Returns:
            True if result should be auto-confirmed.
        """
        # Check for validation errors
        if validation_result.get("errors"):
            return False

        # Check all field confidences
        for field_data in extraction_result.values():
            if not isinstance(field_data, dict):
                continue

            data_source = field_data.get("data_source", {})
            confidence = data_source.get("confidence", 0.0)

            if confidence < threshold:
                return False

        return True

    async def confirm_result(
        self,
        flow_id: int,
        result_id: int,
        confirmed_by: str = "AUTO",
        notes: Optional[str] = None,
    ) -> bool:
        """Confirm an extraction result.

        Args:
            flow_id: Flow ID reference.
            result_id: Result ID to confirm.
            confirmed_by: Who confirmed (AUTO or user ID).
            notes: Optional confirmation notes.

        Returns:
            True if confirmation was successful.
        """
        # In real implementation, save confirmation
        # UPDATE digi_flow_result SET confirmed_at = NOW() WHERE id = :result_id
        # INSERT INTO digi_flow_confirmation ...
        # TODO: Persist confirmation record.

        return True

    async def get_confirmation_status(
        self,
        flow_id: int,
        result_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Get confirmation status for a result.

        Args:
            flow_id: Flow ID reference.
            result_id: Result ID.

        Returns:
            Confirmation status or None if not confirmed.
        """
        # In real implementation, query database
        return None

    async def revoke_confirmation(
        self,
        flow_id: int,
        result_id: int,
        reason: str,
    ) -> bool:
        """Revoke a previous confirmation.

        Args:
            flow_id: Flow ID reference.
            result_id: Result ID.
            reason: Reason for revocation.

        Returns:
            True if revocation was successful.
        """
        # In real implementation, update database
        # UPDATE digi_flow_result SET confirmed_at = NULL WHERE id = :result_id
        return True

    def calculate_overall_confidence(
        self,
        extraction_result: Dict[str, Any],
    ) -> float:
        """Calculate overall confidence for an extraction result.

        Args:
            extraction_result: The extraction result.

        Returns:
            Average confidence across all fields.
        """
        confidences = []

        for field_data in extraction_result.values():
            if not isinstance(field_data, dict):
                continue

            data_source = field_data.get("data_source", {})
            if "confidence" in data_source:
                confidences.append(data_source["confidence"])

        if not confidences:
            return 0.0

        return sum(confidences) / len(confidences)
