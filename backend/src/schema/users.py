import time
import uuid as uuid_module

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from src.schema.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    expert_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


def create_self_referencing_user(engine: Engine, *, username: str, role: str, expert_level: int = 0) -> User:
    """Insert a new user whose created_by references its own id.

    Needed for self-service signup and the one-time admin bootstrap, where
    there is no other existing user to attribute creation to. Relies on
    SQLite's deferred foreign-key checking so the row can transiently
    reference a placeholder id before being corrected to reference itself.

    Uses `engine.raw_connection()` with an explicit transaction rather than
    a SQLAlchemy Core `Connection`/`engine.begin()` - empirically, statements
    run through SQLAlchemy's own transaction management do not actually defer
    the FK check (the INSERT below raises immediately despite `PRAGMA
    defer_foreign_keys` reading back as enabled), while the same statements
    against a raw DBAPI connection defer correctly. Raises the DBAPI's
    `sqlite3.IntegrityError` (e.g. on duplicate username) after rolling back.
    """
    uuid_bytes = uuid_module.uuid4().bytes
    created_at_ms = int(time.time() * 1000)

    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("BEGIN")
        cursor.execute("PRAGMA defer_foreign_keys = ON")
        cursor.execute(
            "INSERT INTO users (uuid, created_at, created_by, username, role, expert_level) "
            "VALUES (?, ?, 0, ?, ?, ?)",
            (uuid_bytes, created_at_ms, username, role, expert_level),
        )
        new_id = cursor.lastrowid
        cursor.execute("UPDATE users SET created_by = ? WHERE id = ?", (new_id, new_id))
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()

    return User(
        id=new_id,
        uuid=uuid_bytes,
        created_at=created_at_ms,
        created_by=new_id,
        username=username,
        role=role,
        expert_level=expert_level,
    )


def count_users(engine: Engine) -> int:
    raw = engine.raw_connection()
    try:
        return raw.cursor().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        raw.close()


def lookup_user_by_uuid(session_factory: sessionmaker, uuid_bytes: bytes) -> User | None:
    with session_factory() as session:
        return session.execute(select(User).where(User.uuid == uuid_bytes)).scalar_one_or_none()


def lookup_user_by_username(session: Session, username: str) -> User | None:
    """Resolve a user by username, case-insensitively.

    Matches the case-insensitive uniqueness enforced on signup (the DB has a
    unique index on ``LOWER(username)``), so a user can log in regardless of
    the casing they type.
    """
    return session.execute(
        select(User).where(func.lower(User.username) == username.lower())
    ).scalar_one_or_none()
