from src import config
from src.bootstrap_admin import seed_admin_from_env
from src.constants import UNKNOWN_CAMERA_UUID
from src.db import make_engine
from src.migrations.runner import run_migrations
from src.schema.cameras import seed_unknown_camera
from src.schema.users import create_self_referencing_user


def test_seed_unknown_camera_noops_without_users(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    assert seed_unknown_camera(engine) is None


def test_seed_unknown_camera_creates_row_owned_by_first_user(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)
    admin = create_self_referencing_user(engine, username="admin", role="admin")

    camera = seed_unknown_camera(engine)

    assert camera is not None
    assert camera.uuid == UNKNOWN_CAMERA_UUID.bytes
    assert camera.title == "Unknown Camera"
    assert camera.created_by == admin.id


def test_seed_unknown_camera_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)
    create_self_referencing_user(engine, username="admin", role="admin")

    seed_unknown_camera(engine)
    # A second boot (or one against an existing database) must not create a
    # duplicate or raise on the unique-title/unique-uuid constraints.
    assert seed_unknown_camera(engine) is None


def test_seed_unknown_camera_runs_after_env_admin_in_same_boot(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEED_ADMIN_USERNAME", "root")
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    engine = make_engine(db_path)

    admin = seed_admin_from_env(engine, str(tmp_path / "auth.db"))
    camera = seed_unknown_camera(engine)

    assert camera is not None
    assert camera.created_by == admin.id
