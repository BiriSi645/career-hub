from pathlib import Path

from app.database import get_db


SQL_DIR = Path(__file__).resolve().parents[1] / "sql"
REVISIONS = (
    ("001_initial_schema", "schema.sql"),
    ("002_company_experiences", "link_experiences.sql"),
)


def upgrade_database():
    connection = get_db()
    with connection.transaction():
        connection.execute("SELECT pg_advisory_xact_lock(708192360)")
        # Reuse the version table from existing installations.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS alembic_version (version_num varchar(32) PRIMARY KEY)
        """)
        versions = [version for version, in connection.execute("SELECT version_num FROM alembic_version")]
        known_versions = [version for version, _ in REVISIONS]
        if versions and (len(versions) != 1 or versions[0] not in known_versions):
            raise RuntimeError(f"Unsupported database revision: {versions}")
        if not versions and connection.execute("SELECT to_regclass('public.users')").fetchone()[0] is not None:
            raise RuntimeError("The database contains Career Hub tables without a recorded revision. Restore or review its schema version before upgrading.")
        start = known_versions.index(versions[0]) + 1 if versions else 0
        for version, filename in REVISIONS[start:]:
            connection.execute((SQL_DIR / filename).read_text(encoding="utf-8"), prepare=False)
            connection.execute("DELETE FROM alembic_version")
            connection.execute("INSERT INTO alembic_version (version_num) VALUES (%s)", (version,))
