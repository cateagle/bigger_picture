from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.api.v1.dataset._metadata import decode_metadata, encode_metadata
from src.constants import IMAGE_STATUS_INT, INT_IMAGE_STATUS, ImageStatus
from src.db import get_db
from src.models.dataset import ImageCreateRequest, ImageResponse, ImageUpdateRequest
from src.schema.dives import Dive
from src.schema.images import Image
from src.schema.users import User
from src.services.assets import (
    read_image_dimensions,
    resolve_asset_path,
    write_base64_image,
)
from src.services.lookups import get_by_uuid
from src.util import apply_partial_update, now_ms

router = APIRouter()


def _to_response(image: Image, db: Session) -> ImageResponse:
    dive = db.get(Dive, image.dive_id)
    creator = db.get(User, image.created_by)
    status = None
    if image.status_id is not None:
        status_enum = INT_IMAGE_STATUS.get(image.status_id)
        status = str(status_enum) if status_enum is not None else None
    return ImageResponse(
        uuid=UUID(bytes=image.uuid),
        created_at=image.created_at,
        created_by=UUID(bytes=creator.uuid),
        filename=image.filename,
        filepath=image.filepath,
        dive=UUID(bytes=dive.uuid),
        status=status,
        size_x=image.size_x,
        size_y=image.size_y,
        metadata=decode_metadata(image.metadata_json),
        difficulty=image.difficulty,
        priority=image.priority,
    )


def _resolve_dive_id(db: Session, dive_uuid: UUID) -> int:
    dive = get_by_uuid(db, Dive, dive_uuid.bytes)
    if dive is None:
        raise HTTPException(status_code=404, detail="Dive not found")
    return dive.id


def _ingest_image(filepath: str, image_b64: str) -> tuple[int, int, Path, bool]:
    """Validate path, write the decoded image, and read its dimensions.

    Returns `(size_x, size_y, path, pre_existed)`. `pre_existed` records whether
    the destination file already existed before writing, so a failed DB insert
    can unlink only the file it actually created (avoiding orphaned assets).
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


@router.post("/create", response_model=ImageResponse, status_code=201)
def create_image(payload: ImageCreateRequest, request: Request, db: Session = Depends(get_db)):
    user = require_current_user(request)

    dive_id = _resolve_dive_id(db, payload.dive_uuid)

    size_x, size_y, path, pre_existed = _ingest_image(payload.filepath, payload.image)

    image = Image(
        uuid=payload.uuid.bytes,
        created_at=now_ms(),
        created_by=user.id,
        filename=payload.filename,
        filepath=payload.filepath,
        dive_id=dive_id,
        status_id=IMAGE_STATUS_INT[ImageStatus.HIDDEN],
        size_x=size_x,
        size_y=size_y,
        metadata_json=encode_metadata(payload.metadata),
        difficulty=payload.difficulty,
        priority=payload.priority,
    )
    db.add(image)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Remove the file we just wrote so a failed create leaves no orphan,
        # but only if it did not pre-exist this request.
        if not pre_existed:
            path.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="Image already exists")
    db.refresh(image)
    return _to_response(image, db)


@router.post("/update", response_model=ImageResponse)
def update_image(payload: ImageUpdateRequest, request: Request, db: Session = Depends(get_db)):
    require_current_user(request)

    image = get_by_uuid(db, Image, payload.uuid.bytes)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    updates = apply_partial_update(
        payload,
        nullable_columns={"metadata_json", "difficulty", "priority"},
        field_map={
            "filename": "filename",
            "filepath": "filepath",
            "metadata": "metadata_json",
            "difficulty": "difficulty",
            "priority": "priority",
        },
    )
    if updates.get("metadata_json") is not None:
        updates["metadata_json"] = encode_metadata(updates["metadata_json"])
    for column, value in updates.items():
        setattr(image, column, value)

    if "dive_uuid" in payload.model_fields_set and payload.dive_uuid is not None:
        image.dive_id = _resolve_dive_id(db, payload.dive_uuid)

    if "image" in payload.model_fields_set and payload.image is not None:
        # Destination is the (possibly updated) filepath, else the current one.
        dest_filepath = image.filepath
        size_x, size_y, _path, _pre_existed = _ingest_image(dest_filepath, payload.image)
        image.size_x = size_x
        image.size_y = size_y

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Image already exists")
    db.refresh(image)
    return _to_response(image, db)


@router.post("/batch/status-change/{new_status}")
def batch_status_change(
    new_status: str,
    uuids: list[UUID],
    request: Request,
    db: Session = Depends(get_db),
):
    require_current_user(request)

    status_id = IMAGE_STATUS_INT.get(new_status)
    if status_id is None:
        raise HTTPException(status_code=422, detail="Unknown image status")

    images: list[Image] = []
    for image_uuid in uuids:
        image = get_by_uuid(db, Image, image_uuid.bytes)
        if image is None:
            raise HTTPException(status_code=404, detail="Image not found")
        images.append(image)

    for image in images:
        image.status_id = status_id

    db.commit()
    return {"updated": len(images)}
