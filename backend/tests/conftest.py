import pytest
from fastapi.testclient import TestClient

from src import config
from src.main import create_app
from src.schema.users import create_self_referencing_user


@pytest.fixture
def app(tmp_path):
    db_path = str(tmp_path / "test.db")
    assets_dir = str(tmp_path / "assets")
    return create_app(database_path=db_path, assets_dir=assets_dir)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seed_user(client):
    def _seed(*, username: str, role: str, expert_level: int = 0):
        engine = client.app.state.engine
        return create_self_referencing_user(engine, username=username, role=role, expert_level=expert_level)

    return _seed


@pytest.fixture
def login_as(client):
    def _login(user):
        client.cookies.set(config.COOKIE_NAME, config.encode_uuid(user.uuid))

    return _login
