from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "backend"))

from app.database import Base  # noqa: E402
from app.models import digi_flow  # noqa: F401,E402


def _table_columns(table_name: str) -> set[str]:
    return set(Base.metadata.tables[table_name].c.keys())


def test_digi_flow_schema_columns():
    columns = _table_columns("digi_flow_schema")
    for name in ["id", "slug", "name", "schema", "version", "status", "created_at"]:
        assert name in columns


def test_digi_flow_config_columns():
    columns = _table_columns("digi_flow_config")
    for name in ["id", "slug", "name", "schema_id", "schema_version", "workflow_config", "prompt_config", "status"]:
        assert name in columns


def test_digi_flow_columns():
    columns = _table_columns("digi_flow")
    for name in ["id", "config_id", "schema_id", "content_type", "content_context", "main_status"]:
        assert name in columns


def test_digi_flow_result_columns():
    columns = _table_columns("digi_flow_result")
    for name in ["id", "flow_id", "data", "plain_data", "data_origin", "version"]:
        assert name in columns


def test_rag_training_data_vector_columns():
    columns = _table_columns("rag_training_data_vector")
    for name in ["id", "flow_id", "config_id", "schema_id", "reference_input", "reference_output", "embedding"]:
        assert name in columns


def test_digi_flow_result_field_audit_columns():
    columns = _table_columns("digi_flow_result_field_audit")
    for name in ["id", "flow_id", "result_id", "field_path", "old_value", "new_value", "reason_code", "audited_at"]:
        assert name in columns
