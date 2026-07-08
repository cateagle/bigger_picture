import time

from sqlalchemy import ForeignKey, Integer, LargeBinary, String
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, mapped_column

from src.constants import UNKNOWN_CAMERA_UUID
from src.schema.base import Base


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    metadata_json: Mapped[str | None] = mapped_column("metadata", String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)


def seed_unknown_camera(engine: Engine) -> Camera | None:
    """Create the well-known "Unknown Camera" row, if it doesn't exist yet.

    Dives created without an explicit camera fall back to this row (fixed
    uuid `UNKNOWN_CAMERA_UUID`). Idempotent and safe to run on every boot.
    `created_by` requires a real user, so this no-ops until at least one user
    exists (e.g. before the first admin has been bootstrapped) - the next
    boot after that will pick it up.
    """
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        existing = cursor.execute(
            "SELECT id FROM cameras WHERE uuid = ?", (UNKNOWN_CAMERA_UUID.bytes,)
        ).fetchone()
        if existing is not None:
            return None

        owner = cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
        if owner is None:
            return None
        owner_id = owner[0]

        created_at_ms = int(time.time() * 1000)
        cursor.execute(
            "INSERT INTO cameras (uuid, created_at, created_by, title, metadata, description) "
            "VALUES (?, ?, ?, ?, NULL, NULL)",
            (UNKNOWN_CAMERA_UUID.bytes, created_at_ms, owner_id, "Unknown Camera"),
        )
        new_id = cursor.lastrowid
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()

    return Camera(
        id=new_id,
        uuid=UNKNOWN_CAMERA_UUID.bytes,
        created_at=created_at_ms,
        created_by=owner_id,
        title="Unknown Camera",
        metadata_json=None,
        description=None,
    )
