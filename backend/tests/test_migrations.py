import sqlite3

import pytest

from src.migrations.runner import run_migrations


def test_applies_cleanly_and_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")

    applied = run_migrations(db_path)
    assert applied == [
        "0001_initial_schema.sql",
        "0002_dive_consistency_triggers.sql",
        "0003_annotation_views.sql",
        "0004_status_descriptions.sql",
        "0005_candidate_vote_uniqueness.sql",
    ]

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


def test_enables_wal_mode_and_full_autovacuum(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA auto_vacuum").fetchone()[0] == 1  # FULL
    finally:
        conn.close()


def test_rerunning_migrations_keeps_wal_and_autovacuum(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    run_migrations(db_path)

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA auto_vacuum").fetchone()[0] == 1
    finally:
        conn.close()


def test_applies_pending_migrations_when_database_is_partially_migrated(tmp_path):
    from pathlib import Path

    db_path = str(tmp_path / "test.db")
    migrations_dir = Path(__file__).resolve().parent.parent / "src" / "migrations"

    # First, apply only 0001 by copying it to a temp migrations dir
    temp_migrations_dir = tmp_path / "migrations_0001_only"
    temp_migrations_dir.mkdir()
    (temp_migrations_dir / "0001_initial_schema.sql").write_text(
        (migrations_dir / "0001_initial_schema.sql").read_text()
    )

    # Initialize database with only 0001
    applied = run_migrations(db_path, migrations_dir=temp_migrations_dir)
    assert applied == ["0001_initial_schema.sql"]

    # Now run migrations with all migrations available - should apply 0002 and 0003 and following ones.
    applied = run_migrations(db_path, migrations_dir=migrations_dir)
    assert 3 <= len(applied)
