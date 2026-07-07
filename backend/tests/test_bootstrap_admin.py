import pytest

from src.bootstrap_admin import bootstrap_admin
from src.constants import Role
from src.db import make_engine
from src.migrations.runner import run_migrations
from src.schema.users import create_self_referencing_user


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
