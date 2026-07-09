import pytest

from src import config
from src.bootstrap_admin import bootstrap_admin, seed_admin_from_env
from src.constants import Role
from src.db import make_engine, make_session_factory
from src.migrations.runner import run_migrations
from src.password_auth.hashing import hash_password, verify_password
from src.password_auth.store import get_password_hash, set_password_hash
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

    user = seed_admin_from_env(engine, str(tmp_path / "auth.db"))

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

    assert seed_admin_from_env(engine, str(tmp_path / "auth.db")) is None
    assert count_users(engine) == 0


def test_seed_admin_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEED_ADMIN_USERNAME", "root")
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)
    auth_db_path = str(tmp_path / "auth.db")

    seed_admin_from_env(engine, auth_db_path)
    # A second boot (or one against an existing database) must not create a
    # duplicate or raise on the unique-username constraint.
    assert seed_admin_from_env(engine, auth_db_path) is None
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
    auth_db_path = str(tmp_path / "auth.db")
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    user = seed_admin_from_env(engine, auth_db_path)

    stored_hash = get_password_hash(auth_db_path, user.uuid)
    assert stored_hash is not None
    assert verify_password("correct horse battery staple", stored_hash)


def test_seed_admin_from_env_password_blank_sets_no_credential(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEED_ADMIN_USERNAME", "root")
    monkeypatch.setattr(config, "SEED_ADMIN_PASSWORD", "")
    auth_db_path = str(tmp_path / "auth.db")
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    user = seed_admin_from_env(engine, auth_db_path)

    assert get_password_hash(auth_db_path, user.uuid) is None


def test_seed_admin_from_env_uses_default_password_fallback(tmp_path):
    """SEED_ADMIN_PASSWORD's default (unset env var) must be a real,
    non-blank fallback - a fresh deployment that only configures
    SEED_ADMIN_USERNAME must still end up with a usable admin login, with no
    additional CLI step required.
    """
    assert config.SEED_ADMIN_PASSWORD  # sanity check the default itself isn't blank

    auth_db_path = str(tmp_path / "auth.db")
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, "SEED_ADMIN_USERNAME", "root")
        user = seed_admin_from_env(engine, auth_db_path)

    stored_hash = get_password_hash(auth_db_path, user.uuid)
    assert stored_hash is not None
    assert verify_password(config.SEED_ADMIN_PASSWORD, stored_hash)


def test_seed_admin_from_env_seeds_password_for_pre_existing_admin(tmp_path, monkeypatch):
    """Covers activating password auth against a database that already had an
    admin from before password auth existed (or was ever configured): no user
    to create, but the auth database has never been touched, so the seed
    admin should still end up with a password.
    """
    monkeypatch.setattr(config, "SEED_ADMIN_USERNAME", "root")
    monkeypatch.setattr(config, "SEED_ADMIN_PASSWORD", "correct horse battery staple")
    auth_db_path = str(tmp_path / "auth.db")
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)
    pre_existing = create_self_referencing_user(engine, username="root", role=Role.ADMIN)

    user = seed_admin_from_env(engine, auth_db_path)

    assert user is not None
    assert user.uuid == pre_existing.uuid
    stored_hash = get_password_hash(auth_db_path, user.uuid)
    assert stored_hash is not None
    assert verify_password("correct horse battery staple", stored_hash)
    assert count_users(engine) == 1  # no duplicate user was created


def test_seed_admin_from_env_does_not_overwrite_once_auth_db_has_any_credential(tmp_path, monkeypatch):
    """Once the password_auth database has been used at all - for anyone,
    not just the seed admin - this must never reset a password an admin has
    since changed.
    """
    monkeypatch.setattr(config, "SEED_ADMIN_USERNAME", "root")
    monkeypatch.setattr(config, "SEED_ADMIN_PASSWORD", "this-should-never-be-applied")
    auth_db_path = str(tmp_path / "auth.db")
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)
    admin = create_self_referencing_user(engine, username="root", role=Role.ADMIN)
    # Some other scientist/admin already has a password - the auth db is "in use".
    other = create_self_referencing_user(engine, username="someone-else", role=Role.SCIENTIST)
    set_password_hash(auth_db_path, other.uuid, hash_password("someone else's password"))

    seed_admin_from_env(engine, auth_db_path)

    assert get_password_hash(auth_db_path, admin.uuid) is None
