from src.constants import Role
from src.create_users import create_user_if_missing, seed_admin_and_scientist
from src.db import make_engine
from src.migrations.runner import run_migrations
from src.schema.users import count_users, create_self_referencing_user


def test_creates_admin_and_scientist_in_empty_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    created = seed_admin_and_scientist(engine, admin_username="admin", scientist_username="scientist")

    assert created["admin"] is not None
    assert created["admin"].role == Role.ADMIN
    assert created["admin"].id == created["admin"].created_by
    assert created["scientist"] is not None
    assert created["scientist"].role == Role.SCIENTIST
    assert count_users(engine) == 2


def test_works_when_users_already_exist(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)
    create_self_referencing_user(engine, username="existing", role="annotator")
    create_self_referencing_user(engine, username="existing-admin", role="admin")

    created = seed_admin_and_scientist(engine, admin_username="admin2", scientist_username="scientist2")

    assert created["admin"] is not None
    assert created["scientist"] is not None
    assert count_users(engine) == 4


def test_skips_taken_username_without_raising(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)
    create_self_referencing_user(engine, username="admin", role="annotator")

    result = create_user_if_missing(engine, username="admin", role=Role.ADMIN)

    assert result is None
    assert count_users(engine) == 1


def test_skip_is_case_insensitive(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)
    create_self_referencing_user(engine, username="Admin", role="annotator")

    result = create_user_if_missing(engine, username="admin", role=Role.ADMIN)

    assert result is None
    assert count_users(engine) == 1


def test_seed_admin_and_scientist_is_rerunnable(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    seed_admin_and_scientist(engine)
    second = seed_admin_and_scientist(engine)

    assert second["admin"] is None
    assert second["scientist"] is None
    assert count_users(engine) == 2
