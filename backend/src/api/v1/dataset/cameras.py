from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.api.v1.dataset._metadata import decode_metadata, encode_metadata
from src.db import get_db
from src.models.dataset import CameraResponse
from src.schema.cameras import Camera
from src.schema.users import User
from src.services.lookups import get_by_uuid
from src.util import apply_partial_update, now_ms

router = APIRouter()


class CameraCreateRequest(BaseModel):
    uuid: UUID
    title: str = Field(min_length=1, max_length=127)
    metadata: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=1023)


class CameraUpdateRequest(BaseModel):
    uuid: UUID
    title: str | None = Field(default=None, min_length=1, max_length=127)
    metadata: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=1023)


def _to_response(camera: Camera, db: Session) -> CameraResponse:
    creator = db.get(User, camera.created_by)
    return CameraResponse(
        uuid=UUID(bytes=camera.uuid),
        created_at=camera.created_at,
        created_by=UUID(bytes=creator.uuid),
        title=camera.title,
        metadata=decode_metadata(camera.metadata_json),
        description=camera.description,
    )


@router.post("/create", response_model=CameraResponse, status_code=201)
def create_camera(payload: CameraCreateRequest, request: Request, db: Session = Depends(get_db)):
    user = require_current_user(request)

    camera = Camera(
        uuid=payload.uuid.bytes,
        created_at=now_ms(),
        created_by=user.id,
        title=payload.title,
        metadata_json=encode_metadata(payload.metadata),
        description=payload.description,
    )
    db.add(camera)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Camera already exists")
    db.refresh(camera)
    return _to_response(camera, db)


@router.post("/update", response_model=CameraResponse)
def update_camera(payload: CameraUpdateRequest, request: Request, db: Session = Depends(get_db)):
    require_current_user(request)

    camera = get_by_uuid(db, Camera, payload.uuid.bytes)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")

    updates = apply_partial_update(
        payload,
        nullable_columns={"metadata_json", "description"},
        field_map={"title": "title", "metadata": "metadata_json", "description": "description"},
    )
    if updates.get("metadata_json") is not None:
        updates["metadata_json"] = encode_metadata(updates["metadata_json"])
    for column, value in updates.items():
        setattr(camera, column, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Camera already exists")
    db.refresh(camera)
    return _to_response(camera, db)
