from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.v1.dataset._metadata import encode_metadata
from src.constants import UNKNOWN_CAMERA_UUID
from src.schema.cameras import Camera
from src.schema.dives import Dive
from src.schema.regions import Region
from src.services.errors import ConflictError
from src.services.lookups import get_by_uuid
from src.util import now_ms


def resolve_region_id(db: Session, region_uuid: UUID) -> int | None:
    region = get_by_uuid(db, Region, region_uuid.bytes)
    return region.id if region is not None else None


def resolve_camera_id(db: Session, camera_uuid: UUID) -> int | None:
    camera = get_by_uuid(db, Camera, camera_uuid.bytes)
    return camera.id if camera is not None else None


def resolve_or_default_camera_id(
    db: Session, camera_uuid: UUID | None, creator_id: int
) -> int | None:
    """Resolve `camera_uuid`, falling back to the well-known "Unknown Camera" row when unset.

    Returns None if `camera_uuid` is given but doesn't resolve to an existing camera.

    The fallback row is normally seeded on startup (see
    `src.schema.cameras.seed_unknown_camera`), but is created here on demand
    if it's somehow still missing, attributed to the requesting user. That
    on-demand insert runs inside a SAVEPOINT (`db.begin_nested()`) rather than
    a plain flush-then-rollback, so a failure there (another concurrent
    request winning the race) only undoes this one insert - not any other
    rows already flushed earlier in the same transaction, as happens when this
    is called partway through a bulk import.
    """
    if camera_uuid is not None:
        return resolve_camera_id(db, camera_uuid)

    camera = get_by_uuid(db, Camera, UNKNOWN_CAMERA_UUID.bytes)
    if camera is not None:
        return camera.id

    try:
        with db.begin_nested():
            camera = Camera(
                uuid=UNKNOWN_CAMERA_UUID.bytes,
                created_at=now_ms(),
                created_by=creator_id,
                title="Unknown Camera",
            )
            db.add(camera)
            db.flush()
    except IntegrityError:
        camera = get_by_uuid(db, Camera, UNKNOWN_CAMERA_UUID.bytes)
        if camera is None:
            raise
    return camera.id


def create_dive(
    db: Session,
    *,
    uuid: UUID,
    title: str,
    metadata: Any | None,
    description: str | None,
    region_id: int,
    camera_id: int,
    creator_id: int,
) -> Dive:
    """Build, add, and flush a new `Dive` row. Does not commit.

    Raises `ConflictError` if the uuid or title already exists.
    """
    dive = Dive(
        uuid=uuid.bytes,
        created_at=now_ms(),
        created_by=creator_id,
        title=title,
        metadata_json=encode_metadata(metadata),
        description=description,
        region_id=region_id,
        camera_id=camera_id,
    )
    db.add(dive)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError("Dive already exists") from exc
    return dive
