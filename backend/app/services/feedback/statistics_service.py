"""Service for tracking feedback and correction statistics."""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import func, select

from app.models.digi_flow import DigiFlow, DigiFlowResult, DigiFlowResultFieldAudit


class StatisticsService:
    """Service for feedback statistics tracking."""

    def __init__(self, db: Any):
        """Initialize statistics service.

        Args:
            db: Database session.
        """
        self.db = db

    async def get_config_statistics(
        self,
        config_id: int,
    ) -> Dict[str, Any]:
        """Get statistics for a configuration.

        Args:
            config_id: Configuration ID.

        Returns:
            Statistics including correction rate.
        """
        total_subquery = (
            select(func.count(DigiFlow.id))
            .where(DigiFlow.config_id == config_id)
            .scalar_subquery()
        )
        manual_subquery = (
            select(func.count(func.distinct(DigiFlowResultFieldAudit.flow_id)))
            .select_from(DigiFlowResultFieldAudit)
            .join(DigiFlow, DigiFlow.id == DigiFlowResultFieldAudit.flow_id)
            .where(DigiFlow.config_id == config_id)
            .scalar_subquery()
        )
        query = select(
            total_subquery.label("total_extractions"),
            manual_subquery.label("manual_corrections"),
        )
        result = await self.db.execute(query)
        stats = result.one()

        total = stats.total_extractions or 0
        manual_corrections = stats.manual_corrections or 0
        auto_confirmed = max(total - manual_corrections, 0)

        correction_rate = manual_corrections / total if total > 0 else 0.0

        return {
            "config_id": config_id,
            "total_extractions": total,
            "auto_confirmed_count": auto_confirmed,
            "manual_correction_count": manual_corrections,
            "correction_rate": correction_rate,
        }

    async def get_problematic_fields(
        self,
        config_id: int,
        threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Get fields with high correction rates.

        Args:
            config_id: Configuration ID.
            threshold: Minimum correction rate to flag.

        Returns:
            List of problematic field statistics.
        """
        total_subquery = (
            select(func.count(DigiFlow.id))
            .where(DigiFlow.config_id == config_id)
            .scalar_subquery()
        )
        query = (
            select(
                DigiFlowResultFieldAudit.field_path.label("field_path"),
                func.count(DigiFlowResultFieldAudit.id).label("corrections"),
                total_subquery.label("total_extractions"),
            )
            .select_from(DigiFlowResultFieldAudit)
            .join(DigiFlow, DigiFlow.id == DigiFlowResultFieldAudit.flow_id)
            .where(DigiFlow.config_id == config_id)
            .group_by(DigiFlowResultFieldAudit.field_path)
        )
        result = await self.db.execute(query)
        field_stats = result.all()

        problematic = []
        for stat in field_stats:
            total = stat.total_extractions or 0
            correction_rate = stat.corrections / total if total > 0 else 0.0
            if correction_rate > threshold:
                problematic.append({
                    "field_path": stat.field_path,
                    "corrections": stat.corrections,
                    "total": total,
                    "correction_rate": correction_rate,
                })

        return problematic

    async def get_daily_statistics(
        self,
        config_id: int,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get daily statistics for a configuration.

        Args:
            config_id: Configuration ID.
            days: Number of days to include.

        Returns:
            Daily statistics.
        """
        flow_daily = (
            select(
                func.date(DigiFlow.created_at).label("day"),
                func.count(DigiFlow.id).label("total_extractions"),
            )
            .where(DigiFlow.config_id == config_id)
            .group_by(func.date(DigiFlow.created_at))
            .subquery()
        )

        corrections_daily = (
            select(
                func.date(DigiFlowResultFieldAudit.audited_at).label("day"),
                func.count(func.distinct(DigiFlowResultFieldAudit.flow_id)).label("manual_corrections"),
            )
            .select_from(DigiFlowResultFieldAudit)
            .join(DigiFlow, DigiFlow.id == DigiFlowResultFieldAudit.flow_id)
            .where(DigiFlow.config_id == config_id)
            .group_by(func.date(DigiFlowResultFieldAudit.audited_at))
            .subquery()
        )

        query = (
            select(
                flow_daily.c.day,
                flow_daily.c.total_extractions,
                func.coalesce(corrections_daily.c.manual_corrections, 0).label("manual_corrections"),
            )
            .select_from(
                flow_daily.outerjoin(
                    corrections_daily,
                    flow_daily.c.day == corrections_daily.c.day,
                )
            )
            .order_by(flow_daily.c.day.desc())
            .limit(days)
        )

        result = await self.db.execute(query)
        rows = result.all()

        daily_stats = []
        for row in rows:
            total = row.total_extractions or 0
            manual = row.manual_corrections or 0
            auto_confirmed = max(total - manual, 0)
            daily_stats.append(
                {
                    "date": row.day.isoformat() if row.day else None,
                    "total_extractions": total,
                    "auto_confirmed_count": auto_confirmed,
                    "manual_correction_count": manual,
                }
            )

        return daily_stats

    async def get_field_correction_history(
        self,
        config_id: int,
        field_path: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get correction history for a specific field.

        Args:
            config_id: Configuration ID.
            field_path: Field path to analyze.
            limit: Maximum records to return.

        Returns:
            List of corrections for the field.
        """
        query = (
            select(
                DigiFlowResultFieldAudit.field_path,
                DigiFlowResultFieldAudit.old_value,
                DigiFlowResultFieldAudit.new_value,
                DigiFlowResultFieldAudit.reason_code,
                DigiFlowResultFieldAudit.reason_text,
                DigiFlowResultFieldAudit.audited_at,
                DigiFlowResultFieldAudit.audited_by,
                DigiFlowResultFieldAudit.result_id,
                DigiFlowResultFieldAudit.result_version,
            )
            .select_from(DigiFlowResultFieldAudit)
            .join(DigiFlow, DigiFlow.id == DigiFlowResultFieldAudit.flow_id)
            .where(
                DigiFlow.config_id == config_id,
                DigiFlowResultFieldAudit.field_path == field_path,
            )
            .order_by(DigiFlowResultFieldAudit.audited_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "field_path": row.field_path,
                "old_value": row.old_value,
                "new_value": row.new_value,
                "reason_code": row.reason_code,
                "reason_text": row.reason_text,
                "audited_at": row.audited_at,
                "audited_by": row.audited_by,
                "result_id": row.result_id,
                "result_version": row.result_version,
            }
            for row in rows
        ]

    async def get_confidence_distribution(
        self,
        config_id: int,
    ) -> Dict[str, int]:
        """Get distribution of confidence scores.

        Args:
            config_id: Configuration ID.

        Returns:
            Distribution by confidence bucket.
        """
        latest_versions = (
            select(
                DigiFlowResult.flow_id,
                func.max(DigiFlowResult.version).label("max_version"),
            )
            .group_by(DigiFlowResult.flow_id)
            .subquery()
        )
        query = (
            select(DigiFlowResult.data)
            .join(
                latest_versions,
                (DigiFlowResult.flow_id == latest_versions.c.flow_id)
                & (DigiFlowResult.version == latest_versions.c.max_version),
            )
            .join(DigiFlow, DigiFlow.id == DigiFlowResult.flow_id)
            .where(DigiFlow.config_id == config_id)
        )
        result = await self.db.execute(query)
        rows = result.scalars().all()

        buckets = {
            "very_low": 0,    # < 0.5
            "low": 0,         # 0.5 - 0.7
            "medium": 0,      # 0.7 - 0.9
            "high": 0,        # >= 0.9
        }

        for data in rows:
            if not isinstance(data, dict):
                continue
            for field_data in data.values():
                if not isinstance(field_data, dict):
                    continue
                confidence = field_data.get("data_source", {}).get("confidence")
                if not isinstance(confidence, (int, float)):
                    continue
                if confidence < 0.5:
                    buckets["very_low"] += 1
                elif confidence < 0.7:
                    buckets["low"] += 1
                elif confidence < 0.9:
                    buckets["medium"] += 1
                else:
                    buckets["high"] += 1

        return buckets

    async def get_auto_confirmation_rate(
        self,
        config_id: int,
    ) -> float:
        """Get auto-confirmation rate for a configuration.

        Args:
            config_id: Configuration ID.

        Returns:
            Ratio of auto-confirmed results.
        """
        stats = await self.get_config_statistics(config_id)
        total = stats.get("total_extractions", 0)
        auto_confirmed = stats.get("auto_confirmed_count", 0)

        return auto_confirmed / total if total > 0 else 0.0
