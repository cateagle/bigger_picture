import sqlite3

import pytest

from src.migrations.runner import run_migrations


def test_applies_cleanly_and_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")

    applied = run_migrations(db_path)
    assert applied == ["0001_initial_schema.sql"]

    applied_again = run_migrations(db_path)
    assert applied_again == []


def test_role_check_constraint_is_enforced(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)

    conn = sqlite3.connect(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (uuid, created_at, created_by, username, role, expert_level) "
                "VALUES (?, 0, 1, 'someone', 'not-a-role', 0)",
                (b"0" * 16,),
            )
    finally:
        conn.close()


def test_username_unique_case_insensitive(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO users (uuid, created_at, created_by, username, role, expert_level) "
            "VALUES (?, 0, 1, 'Alice', 'admin', 0)",
            (b"1" * 16,),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (uuid, created_at, created_by, username, role, expert_level) "
                "VALUES (?, 0, 1, 'alice', 'admin', 0)",
                (b"2" * 16,),
            )
    finally:
        conn.close()
