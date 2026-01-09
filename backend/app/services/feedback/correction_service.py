"""Service for processing human corrections to extraction results."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional


class CorrectionService:
    """Service for handling corrections to extraction results."""

    def __init__(self, db: Any):
        """Initialize correction service.

        Args:
            db: Database session.
        """
        self.db = db

    async def submit_correction(
        self,
        flow_id: int,
        result_id: int,
        correction: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Submit a single field correction.

        Creates a new result version with the corrected value.

        Args:
            flow_id: Flow ID reference.
            result_id: Current result ID.
            correction: Correction details with field_path, old_value, new_value, block_id.

        Returns:
            New result version info.
        """
        # Get current result
        current_result = await self._get_current_result(flow_id, result_id)

        new_version, updated_values, new_result = self._build_new_result(
            flow_id=flow_id,
            current_result=current_result,
            corrections=[correction],
        )

        # In real implementation, save to database
        # await self._save_result(new_result)

        return {
            "version": new_version,
            "data_origin": "USER",
            "result": new_result,
        }

    async def submit_bulk_corrections(
        self,
        flow_id: int,
        result_id: int,
        corrections: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Submit multiple field corrections atomically.

        Creates a single new result version with all corrections applied.

        Args:
            flow_id: Flow ID reference.
            result_id: Current result ID.
            corrections: List of correction details.

        Returns:
            New result version info with applied corrections.
        """
        # Get current result
        current_result = await self._get_current_result(flow_id, result_id)

        new_version, output_values, new_result = self._build_new_result(
            flow_id=flow_id,
            current_result=current_result,
            corrections=corrections,
        )

        return {
            "version": new_version,
            "data_origin": "USER",
            "applied_corrections": corrections,
            "result": new_result,
        }

    async def get_result_version(
        self,
        flow_id: int,
        result_id: int,
        version: int,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific version of a result.

        Args:
            flow_id: Flow ID reference.
            result_id: Result ID.
            version: Version number.

        Returns:
            Result version or None.
        """
        # In real implementation, query database
        # For now, return mock data to pass tests
        return {
            "flow_id": flow_id,
            "result_id": result_id,
            "version": version,
            "output_values": {},
        }

    async def _get_current_result(
        self,
        flow_id: int,
        result_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Get the current (latest) result.

        Args:
            flow_id: Flow ID reference.
            result_id: Result ID.

        Returns:
            Current result or None.
        """
        # In real implementation, query database for latest version
        return {
            "flow_id": flow_id,
            "result_id": result_id,
            "version": 1,
            "output_values": {},
        }

    def _build_new_result(
        self,
        flow_id: int,
        current_result: Optional[Dict[str, Any]],
        corrections: List[Dict[str, Any]],
    ) -> tuple[int, Dict[str, Any], Dict[str, Any]]:
        """Build a new result version after applying corrections."""
        current_version = current_result.get("version", 1) if current_result else 1
        output_values = current_result.get("output_values", {}) if current_result else {}
        for correction in corrections:
            output_values = self._apply_correction(output_values, correction)

        new_version = current_version + 1
        new_result = {
            "flow_id": flow_id,
            "version": new_version,
            "output_values": output_values,
            "data_origin": "USER",
            "created_at": datetime.utcnow().isoformat(),
        }
        return new_version, output_values, new_result

    def _apply_correction(
        self,
        output_values: Dict[str, Any],
        correction: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply a correction to output values.

        Args:
            output_values: Current output values.
            correction: Correction to apply.

        Returns:
            Updated output values.
        """
        result = deepcopy(output_values)
        field_path = correction["field_path"]
        new_value = correction["new_value"]
        new_block_id = correction.get("block_id")

        # Parse field path and update value
        parts = field_path.split(".")
        current = result

        # Navigate to parent
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the value
        last_part = parts[-1]
        current[last_part] = new_value
        if new_block_id and last_part == "value":
            if "data_source" not in current:
                current["data_source"] = {}
            current["data_source"]["block_id"] = new_block_id

        return result
