import pytest
from fastapi.testclient import TestClient

from src import config
from src.csrf import CSRF_HEADER_NAME, compute_csrf_token
from src.main import create_app
from src.password_auth.hashing import hash_password
from src.password_auth.store import set_password_hash
from src.schema.users import create_self_referencing_user


@pytest.fixture
def app(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    # Drive the app's StaticFiles mount and `resolve_asset_path` off the same
    # global so there's a single source of truth for the assets directory.
    monkeypatch.setattr(config, "ASSETS_DIR", str(tmp_path / "assets"))
    monkeypatch.setattr(config, "IMPORT_DIR", str(tmp_path / "import"))
    monkeypatch.setattr(config, "BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setattr(config, "AUTH_DATABASE_PATH", str(tmp_path / "auth.db"))
    return create_app(database_path=db_path)


@pytest.fixture
def assets_dir(tmp_path):
    """The assets directory the app is built against (see the `app` fixture)."""
    return str(tmp_path / "assets")


@pytest.fixture
def import_dir(tmp_path):
    """The import working directory the app is built against (see the `app` fixture)."""
    return str(tmp_path / "import")


@pytest.fixture
def backup_dir(tmp_path):
    """The backup directory the app is built against (see the `app` fixture)."""
    return str(tmp_path / "backups")


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
        # Real logins get this via the CSRF cookie (see auth/router.py's
        # _set_csrf_cookie); this bypass fixture sets the client's default
        # header directly since it never goes through that response.
        client.headers[CSRF_HEADER_NAME] = compute_csrf_token(user.uuid)

    return _login


@pytest.fixture
def set_password(client):
    """Store a password hash for a user directly, bypassing the API."""

    def _set_password(user, password: str):
        set_password_hash(config.AUTH_DATABASE_PATH, user.uuid, hash_password(password))

    return _set_password
