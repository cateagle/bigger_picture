from src import config
from src.db import make_engine
from src.migrations.runner import run_migrations


def test_connect_listener_sets_pragmas(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        assert cursor.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert cursor.execute("PRAGMA busy_timeout").fetchone()[0] == config.SQLITE_BUSY_TIMEOUT_MS
        assert cursor.execute("PRAGMA synchronous").fetchone()[0] == 1  # NORMAL
    finally:
        raw.close()
    engine.dispose()
