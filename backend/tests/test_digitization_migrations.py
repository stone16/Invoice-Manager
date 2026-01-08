from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _migration_text() -> str:
    migrations_dir = _repo_root() / "backend" / "migrations"
    contents = []
    for path in sorted(migrations_dir.glob("V*__*.sql")):
        contents.append(path.read_text(encoding="utf-8"))
    return "\n".join(contents).lower()


def test_migrations_create_required_tables():
    text = _migration_text()
    for table in [
        "digi_flow_schema",
        "digi_flow_config",
        "digi_flow",
        "digi_flow_result",
        "rag_training_data_vector",
        "digi_flow_result_field_audit",
    ]:
        assert f"create table {table}" in text


def test_migrations_include_vector_and_hnsw_index():
    text = _migration_text()
    assert "vector(1536)" in text
    assert "using hnsw" in text
