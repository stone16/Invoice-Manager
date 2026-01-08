from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_docker_compose_uses_pgvector_image():
    compose = (_repo_root() / "docker-compose.yml").read_text(encoding="utf-8")
    assert "pgvector/pgvector" in compose, "docker-compose should use pgvector-enabled image"


def test_pgvector_extension_migration_exists():
    migrations_dir = _repo_root() / "backend" / "migrations"
    migration_files = sorted(migrations_dir.glob("V*__*.sql"))
    assert migration_files, "expected Flyway migration files for pgvector setup"
    migration_text = "\n".join(path.read_text(encoding="utf-8") for path in migration_files)
    assert "CREATE EXTENSION IF NOT EXISTS vector" in migration_text
