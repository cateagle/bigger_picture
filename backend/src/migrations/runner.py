import sqlite3
import time
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent


def run_migrations(database_path: str, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply any pending .sql migration files (sorted by filename) to the given
    SQLite database, tracking what's already been applied in a bookkeeping
    table. Each file is applied atomically. Returns the list of filenames that
    were newly applied.

    Migration files must not contain their own BEGIN/COMMIT/PRAGMA
    foreign_keys statements - the runner supplies the transaction wrapper.
    """
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename    TEXT    NOT NULL PRIMARY KEY,
                applied_at  INTEGER NOT NULL
            )
            """
        )
        conn.commit()

        already_applied = {
            row[0] for row in conn.execute("SELECT filename FROM schema_migrations")
        }

        pending = sorted(
            p.name for p in migrations_dir.glob("*.sql") if p.name not in already_applied
        )

        applied_now = []
        for filename in pending:
            sql_text = (migrations_dir / filename).read_text()
            script = f"BEGIN;\n{sql_text}\nCOMMIT;"
            try:
                conn.executescript(script)
            except Exception:
                conn.rollback()
                raise RuntimeError(f"Migration {filename} failed to apply")
            conn.execute(
                "INSERT INTO schema_migrations (filename, applied_at) VALUES (?, ?)",
                (filename, int(time.time() * 1000)),
            )
            conn.commit()
            applied_now.append(filename)

        return applied_now
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    from src import config

    parser = argparse.ArgumentParser(description="Apply pending SQL migrations")
    parser.add_argument("--database-path", default=config.DATABASE_PATH)
    args = parser.parse_args()

    applied = run_migrations(args.database_path)
    if applied:
        print(f"Applied {len(applied)} migration(s): {', '.join(applied)}")
    else:
        print("No pending migrations.")
