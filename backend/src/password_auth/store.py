import time
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from src.password_auth.models import Base, PasswordCredential

# Keyed by database_path. A given path is only ever opened once per process -
# safe here since the whole app runs single-process (see src/main.py).
_session_factories: dict[str, sessionmaker] = {}


def _make_engine(database_path: str) -> Engine:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{database_path}", future=True)

    @event.listens_for(engine, "connect")
    def _set_busy_timeout(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA busy_timeout = 5000")

    Base.metadata.create_all(engine)
    return engine


def _get_session_factory(database_path: str) -> sessionmaker:
    factory = _session_factories.get(database_path)
    if factory is None:
        engine = _make_engine(database_path)
        factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
        _session_factories[database_path] = factory
    return factory


def get_password_hash(database_path: str, user_uuid: bytes) -> str | None:
    with _get_session_factory(database_path)() as session:
        credential = session.get(PasswordCredential, user_uuid)
        return credential.password_hash if credential is not None else None


def has_password(database_path: str, user_uuid: bytes) -> bool:
    return get_password_hash(database_path, user_uuid) is not None


def has_any_password(database_path: str) -> bool:
    """Whether the password_auth database has ever had a credential stored,
    for anyone. Used to detect "the auth database has never been touched" -
    e.g. to decide whether it's still safe to seed a default admin password
    without risking overwriting one an admin has since changed.
    """
    with _get_session_factory(database_path)() as session:
        return session.execute(select(PasswordCredential.user_uuid).limit(1)).first() is not None


def set_password_hash(database_path: str, user_uuid: bytes, password_hash: str) -> None:
    with _get_session_factory(database_path)() as session:
        credential = session.get(PasswordCredential, user_uuid)
        updated_at = int(time.time() * 1000)
        if credential is None:
            session.add(
                PasswordCredential(user_uuid=user_uuid, password_hash=password_hash, updated_at=updated_at)
            )
        else:
            credential.password_hash = password_hash
            credential.updated_at = updated_at
        session.commit()


def delete_password_hash(database_path: str, user_uuid: bytes) -> None:
    with _get_session_factory(database_path)() as session:
        credential = session.get(PasswordCredential, user_uuid)
        if credential is not None:
            session.delete(credential)
            session.commit()
