import sqlite3
import time
from pathlib import Path

from src import config

MIGRATIONS_DIR = Path(__file__).resolve().parent


def _apply_startup_pragmas(conn: sqlite3.Connection, busy_timeout_ms: int) -> None:
    """Apply the database-level pragmas that only need to be set once - they
    persist in the file header and survive reconnects - plus a defensive
    busy_timeout for this connection in case another process is migrating
    or holding a lock on the same database concurrently.

    Must run before anything else on this connection: no transaction may be
    active yet, since both journal_mode and VACUUM fail inside an explicit
    transaction.
    """
    conn.execute(f"PRAGMA busy_timeout = {busy_timeout_ms}")
    conn.execute("PRAGMA journal_mode = WAL")

    # auto_vacuum: 0=NONE, 1=FULL, 2=INCREMENTAL. INCREMENTAL would require a
    # periodic `PRAGMA incremental_vacuum` call to actually reclaim space,
    # and this codebase has no scheduler to run one, so FULL ("set and
    # forget") is used instead.
    (current_auto_vacuum,) = conn.execute("PRAGMA auto_vacuum").fetchone()
    if current_auto_vacuum != 1:
        conn.execute("PRAGMA auto_vacuum = FULL")
        # Changing auto_vacuum on a non-empty database only takes effect
        # after a VACUUM; cheap/harmless to also run on a fresh, empty
        # database. Must run outside any BEGIN/COMMIT. Runs at most once -
        # subsequent startups see auto_vacuum already FULL and skip this.
        conn.execute("VACUUM")


def run_migrations(
    database_path: str,
    migrations_dir: Path = MIGRATIONS_DIR,
    busy_timeout_ms: int = config.SQLITE_BUSY_TIMEOUT_MS,
) -> list[str]:
    """Apply any pending .sql migration files (sorted by filename) to the given
    SQLite database, tracking what's already been applied in a bookkeeping
    table. Each file is applied atomically. Returns the list of filenames that
    were newly applied.

    Also ensures the database is in WAL journal mode with FULL auto_vacuum
    enabled (see `_apply_startup_pragmas`) and sets a busy_timeout on this
    connection.

    Migration files must not contain their own BEGIN/COMMIT/PRAGMA
    foreign_keys statements - the runner supplies the transaction wrapper.
    """
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    try:
        _apply_startup_pragmas(conn, busy_timeout_ms)

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

    parser = argparse.ArgumentParser(description="Apply pending SQL migrations")
    parser.add_argument("--database-path", default=config.DATABASE_PATH)
    args = parser.parse_args()

    applied = run_migrations(args.database_path)
    if applied:
        print(f"Applied {len(applied)} migration(s): {', '.join(applied)}")
    else:
        print("No pending migrations.")
