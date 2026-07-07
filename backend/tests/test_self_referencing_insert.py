import sqlite3

from src.db import make_engine
from src.migrations.runner import run_migrations
from src.schema.users import create_self_referencing_user


def test_self_reference_and_no_fk_violations(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    user = create_self_referencing_user(engine, username="alice", role="admin")

    assert user.id == user.created_by

    raw = sqlite3.connect(db_path)
    try:
        raw.execute("PRAGMA foreign_keys = ON")
        violations = raw.execute("PRAGMA foreign_key_check").fetchall()
        assert violations == []
    finally:
        raw.close()
