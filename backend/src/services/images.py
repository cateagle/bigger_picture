from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.v1.dataset._metadata import encode_metadata
from src.schema.dives import Dive
from src.schema.images import Image
from src.services.assets import read_image_dimensions, resolve_asset_path, write_base64_image
from src.services.errors import ConflictError
from src.services.lookups import get_by_uuid
from src.util import now_ms


def resolve_dive_id(db: Session, dive_uuid: UUID) -> int | None:
    dive = get_by_uuid(db, Dive, dive_uuid.bytes)
    return dive.id if dive is not None else None


def ingest_base64_image(filepath: str, image_b64: str) -> tuple[int, int, Path, bool]:
    """Validate path, write the decoded image, and read its dimensions.

    Returns `(size_x, size_y, path, pre_existed)`. `pre_existed` records whether
    the destination file already existed before writing, so a failed DB insert
    can unlink only the file it actually created (avoiding orphaned assets).

    Used by the single-item image create endpoint, where the image bytes
    arrive base64-encoded in the request body.
    """
    try:
        path = resolve_asset_path(filepath)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid filepath")
    pre_existed = path.exists()
    try:
        write_base64_image(path, image_b64)
    except Exception:  # invalid base64 / write failure
        if not pre_existed:
            path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="Invalid image data")
    try:
        size_x, size_y = read_image_dimensions(path)
    except ValueError:
        if not pre_existed:
            path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="Could not decode image")
    return size_x, size_y, path, pre_existed


def create_image(
    db: Session,
    *,
    uuid: UUID,
    filename: str,
    filepath: str,
    dive_id: int,
    status_id: int,
    size_x: int,
    size_y: int,
    metadata: Any | None,
    difficulty: int | None,
    priority: int | None,
    creator_id: int,
) -> Image:
    """Build, add, and flush a new `Image` row. Does not commit and does no file I/O.

    Raises `ConflictError` if the uuid or filepath already exists.
    """
    image = Image(
        uuid=uuid.bytes,
        created_at=now_ms(),
        created_by=creator_id,
        filename=filename,
        filepath=filepath,
        dive_id=dive_id,
        status_id=status_id,
        size_x=size_x,
        size_y=size_y,
        metadata_json=encode_metadata(metadata),
        difficulty=difficulty,
        priority=priority,
    )
    db.add(image)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError("Image already exists") from exc
    return image
