from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
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
    """Request used to create a new camera in the metadata table."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuid": "8f8b65dc-fbf2-4dfb-bff2-f34072bb97e2",
                "title": "GoPro Hero 11",
                "metadata": None,
                "description": None,
            }
        }
    )

    uuid: UUID = Field(description="Unique identifier to assign to the new camera.")

    title: str = Field(
        min_length=1,
        max_length=127,
        description="Display name of the camera. Must be unique.",
    )

    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional arbitrary JSON object to attach to the camera.",
    )

    description: str | None = Field(
        default=None,
        max_length=1023,
        description="Optional free-text description of the camera.",
    )


class CameraUpdateRequest(BaseModel):
    """Request Model used to partially update an existing camera.

    Only the fields explicitly supplied are changed; omitted fields are left
    untouched. Sending an explicit null for title is also a no-op, since it
    is not a nullable column.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuid": "8f8b65dc-fbf2-4dfb-bff2-f34072bb97e2",
                "title": "GoPro Hero 11 (renamed)",
            }
        }
    )

    uuid: UUID = Field(description="Unique identifier of the camera to update.")

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=127,
        description="New display name. Must be unique. Omit to leave unchanged.",
    )

    metadata: dict[str, Any] | None = Field(
        default=None,
        description="New metadata object. Send null to clear it, or omit to leave unchanged.",
    )

    description: str | None = Field(
        default=None,
        max_length=1023,
        description="New description. Send null to clear it, or omit to leave unchanged.",
    )


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


@router.post(
    "/create",
    response_model=CameraResponse,
    status_code=201,
    summary="Create Camera",
    description="""
Create a new camera, identified by uuid, with the given title and optional metadata and description. Requires the scientist role.

Fails with 409 if a camera with this uuid or title already exists.
""",
)
def create_camera(
    payload: CameraCreateRequest, request: Request, db: Session = Depends(get_db)
):
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


@router.post(
    "/update",
    response_model=CameraResponse,
    summary="Update Camera",
    description="""
Partially update an existing camera, identified by uuid. Requires the scientist role.

Only the fields supplied in the request are changed; omitted fields are left as-is. Sending an explicit null for title is a no-op, but sending an explicit null for metadata or description clears it.

Fails with 404 if the uuid is not found, or 409 if the new title is already taken.
""",
)
def update_camera(
    payload: CameraUpdateRequest, request: Request, db: Session = Depends(get_db)
):
    require_current_user(request)

    camera = get_by_uuid(db, Camera, payload.uuid.bytes)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")

    updates = apply_partial_update(
        payload,
        nullable_columns={"metadata_json", "description"},
        field_map={
            "title": "title",
            "metadata": "metadata_json",
            "description": "description",
        },
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
