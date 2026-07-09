import pytest

from src import config
from src.bootstrap_admin import bootstrap_admin, seed_admin_from_env
from src.constants import Role
from src.db import make_engine, make_session_factory
from src.migrations.runner import run_migrations
from src.password_auth.hashing import verify_password
from src.password_auth.store import get_password_hash
from src.schema.users import count_users, create_self_referencing_user, lookup_user_by_username


def test_bootstrap_creates_self_referencing_admin(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    user = bootstrap_admin(engine, "admin")

    assert user.role == Role.ADMIN
    assert user.id == user.created_by


def test_bootstrap_refuses_when_users_exist(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    create_self_referencing_user(engine, username="existing", role="annotator")

    with pytest.raises(RuntimeError):
        bootstrap_admin(engine, "admin")


def test_seed_admin_from_env_creates_admin(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEED_ADMIN_USERNAME", "root")
    monkeypatch.setattr(config, "SEED_ADMIN_EXPERT_LEVEL", 3)
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    user = seed_admin_from_env(engine)

    assert user is not None
    assert user.role == Role.ADMIN
    assert user.expert_level == 3
    with make_session_factory(engine)() as session:
        assert lookup_user_by_username(session, "root") is not None


def test_seed_admin_disabled_when_username_blank(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEED_ADMIN_USERNAME", "")
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    assert seed_admin_from_env(engine) is None
    assert count_users(engine) == 0


def test_seed_admin_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEED_ADMIN_USERNAME", "root")
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    seed_admin_from_env(engine)
    # A second boot (or one against an existing database) must not create a
    # duplicate or raise on the unique-username constraint.
    assert seed_admin_from_env(engine) is None
    assert count_users(engine) == 1


def test_bootstrap_admin_with_password_stores_credential(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "AUTH_DATABASE_PATH", str(tmp_path / "auth.db"))
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    user = bootstrap_admin(engine, "admin", password="correct horse battery staple")

    stored_hash = get_password_hash(config.AUTH_DATABASE_PATH, user.uuid)
    assert stored_hash is not None
    assert verify_password("correct horse battery staple", stored_hash)


def test_bootstrap_admin_without_password_stores_no_credential(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "AUTH_DATABASE_PATH", str(tmp_path / "auth.db"))
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    user = bootstrap_admin(engine, "admin")

    assert get_password_hash(config.AUTH_DATABASE_PATH, user.uuid) is None


def test_seed_admin_from_env_with_password_env_var_sets_credential(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEED_ADMIN_USERNAME", "root")
    monkeypatch.setattr(config, "SEED_ADMIN_PASSWORD", "correct horse battery staple")
    monkeypatch.setattr(config, "AUTH_DATABASE_PATH", str(tmp_path / "auth.db"))
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    user = seed_admin_from_env(engine)

    stored_hash = get_password_hash(config.AUTH_DATABASE_PATH, user.uuid)
    assert stored_hash is not None
    assert verify_password("correct horse battery staple", stored_hash)


def test_seed_admin_from_env_password_blank_sets_no_credential(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEED_ADMIN_USERNAME", "root")
    monkeypatch.setattr(config, "SEED_ADMIN_PASSWORD", "")
    monkeypatch.setattr(config, "AUTH_DATABASE_PATH", str(tmp_path / "auth.db"))
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    user = seed_admin_from_env(engine)

    assert get_password_hash(config.AUTH_DATABASE_PATH, user.uuid) is None
