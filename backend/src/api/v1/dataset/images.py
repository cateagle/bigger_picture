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
    move_asset,
    read_image_dimensions,
    resolve_asset_path,
    write_base64_image,
    write_temp_image,
)
from src.services.lookups import get_by_uuid, image_has_point_annotations
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


@router.post(
    "/create",
    response_model=ImageResponse,
    status_code=201,
    summary="Create Image",
    description="""
Upload a new image, identified by uuid, into an existing dive. The image bytes are supplied base64-encoded and written to disk at filepath; width and height are computed from the decoded image. Requires the scientist role.

The image is always created with status "hidden".

Fails with 404 if the dive does not exist, 422 if filepath is invalid or the image data cannot be decoded, or 409 if an image with this uuid or filepath already exists.
""",
)
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


@router.post(
    "/update",
    response_model=ImageResponse,
    summary="Update Image",
    description="""
Partially update an existing image, identified by uuid, optionally replacing its file. Requires the scientist role.

Only the fields supplied in the request are changed; omitted fields are left as-is. Sending an explicit null for filename, filepath, or dive_uuid is a no-op, but sending an explicit null for metadata, difficulty, or priority clears it.

Fails with 404 if the uuid or dive_uuid is not found, 422 if filepath is invalid or the replacement image data cannot be decoded, or 409 if the new image data would change the image's dimensions while point annotations referencing it exist, or if an image with the new filepath already exists.
""",
)
def update_image(payload: ImageUpdateRequest, request: Request, db: Session = Depends(get_db)):
    require_current_user(request)

    image = get_by_uuid(db, Image, payload.uuid.bytes)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    # Snapshot the current on-disk state before any DB mutation, so file ops
    # (deferred until after a successful commit) can reference the old location.
    old_filepath = image.filepath
    old_resolved = resolve_asset_path(old_filepath)
    old_size = (image.size_x, image.size_y)

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

    # Determine the target (final) on-disk path. `apply_partial_update` already
    # applied `image.filepath` above when the key was present + non-null.
    filepath_changing = (
        "filepath" in payload.model_fields_set
        and payload.filepath is not None
        and payload.filepath != old_filepath
    )
    if "filepath" in payload.model_fields_set and payload.filepath is not None:
        try:
            new_resolved = resolve_asset_path(image.filepath)
        except ValueError:
            db.rollback()
            raise HTTPException(status_code=422, detail="Invalid filepath")
    else:
        new_resolved = old_resolved

    temp_path: Path | None = None
    if "image" in payload.model_fields_set and payload.image is not None:
        try:
            temp_path = write_temp_image(payload.image)
        except ValueError:
            db.rollback()
            raise HTTPException(status_code=422, detail="Invalid image data")
        try:
            new_size = read_image_dimensions(temp_path)
        except ValueError:
            temp_path.unlink(missing_ok=True)
            db.rollback()
            raise HTTPException(status_code=422, detail="Could not decode image")

        if new_size != old_size and image_has_point_annotations(db, image.id):
            # Reject before anything on disk has moved; disk stays untouched.
            temp_path.unlink(missing_ok=True)
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Cannot change image dimensions while point annotations exist",
            )
        image.size_x, image.size_y = new_size

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="Image already exists")

    # DB committed. Now perform file ops: move the existing file first, then
    # swap the new blob in at the final path.
    if filepath_changing:
        move_asset(old_resolved, new_resolved)
    if temp_path is not None:
        move_asset(temp_path, new_resolved)

    db.refresh(image)
    return _to_response(image, db)


@router.post(
    "/batch/status-change/{new_status}",
    summary="Batch Change Image Status",
    description="""
Set the status of every image in the given list of uuids to new_status. Requires the scientist role.

Valid statuses are hidden, open, review_pending, finalized, and deleted.

Fails with 422 if new_status is not a recognized status, or 404 if any uuid does not resolve to an existing image (no images are updated in that case).
""",
)
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
