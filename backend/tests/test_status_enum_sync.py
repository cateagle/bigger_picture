import sqlite3

from src.constants import (
    ANNOTATION_STATUS_INT,
    CANDIDATE_STATUS_INT,
    IMAGE_STATUS_INT,
    INT_ANNOTATION_STATUS,
    INT_CANDIDATE_STATUS,
    INT_IMAGE_STATUS,
    INT_PAIR_STATUS,
    PAIR_STATUS_INT,
)
from src.migrations.runner import run_migrations

STATUS_TABLES = [
    ("image_statuses", INT_IMAGE_STATUS),
    ("pair_statuses", INT_PAIR_STATUS),
    ("candidate_statuses", INT_CANDIDATE_STATUS),
    ("annotation_statuses", INT_ANNOTATION_STATUS),
]

REVERSE_DICTS = [
    (INT_IMAGE_STATUS, IMAGE_STATUS_INT),
    (INT_PAIR_STATUS, PAIR_STATUS_INT),
    (INT_CANDIDATE_STATUS, CANDIDATE_STATUS_INT),
    (INT_ANNOTATION_STATUS, ANNOTATION_STATUS_INT),
]


def test_seed_rows_match_python_enums(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)

    conn = sqlite3.connect(db_path)
    try:
        for table_name, int_to_enum in STATUS_TABLES:
            rows = conn.execute(f"SELECT id, title FROM {table_name} ORDER BY id").fetchall()
            db_values = {row[0]: row[1] for row in rows}
            expected = {k: v.value for k, v in int_to_enum.items()}
            assert db_values == expected, table_name
            assert len(rows) == len(int_to_enum), table_name
    finally:
        conn.close()


def test_forward_and_reverse_dicts_are_inverses():
    for int_to_enum, enum_to_int in REVERSE_DICTS:
        assert {v: k for k, v in int_to_enum.items()} == enum_to_int
