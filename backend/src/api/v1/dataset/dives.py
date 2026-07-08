from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.api.v1.dataset._metadata import decode_metadata, encode_metadata
from src.db import get_db
from src.models.dataset import (
    DiveCreateRequest,
    DiveListResponse,
    DiveResponse,
    DiveUpdateRequest,
)
from src.schema.cameras import Camera
from src.schema.dives import Dive
from src.schema.regions import Region
from src.schema.users import User
from src.services.dives import create_dive as _create_dive_row
from src.services.dives import resolve_camera_id as _resolve_camera_id_or_none
from src.services.dives import resolve_or_default_camera_id
from src.services.dives import resolve_region_id as _resolve_region_id_or_none
from src.services.errors import ConflictError
from src.services.lookups import get_by_uuid
from src.util import apply_partial_update

router = APIRouter()


def _to_response(dive: Dive, db: Session) -> DiveResponse:
    region = db.get(Region, dive.region_id)
    camera = db.get(Camera, dive.camera_id)
    creator = db.get(User, dive.created_by)
    return DiveResponse(
        uuid=UUID(bytes=dive.uuid),
        created_at=dive.created_at,
        created_by=UUID(bytes=creator.uuid),
        title=dive.title,
        metadata=decode_metadata(dive.metadata_json),
        description=dive.description,
        region=UUID(bytes=region.uuid),
        camera=UUID(bytes=camera.uuid),
    )


def _resolve_region_id(db: Session, region_uuid: UUID) -> int:
    region_id = _resolve_region_id_or_none(db, region_uuid)
    if region_id is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return region_id


def _resolve_camera_id(db: Session, camera_uuid: UUID) -> int:
    camera_id = _resolve_camera_id_or_none(db, camera_uuid)
    if camera_id is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera_id


def _resolve_or_default_camera_id(
    db: Session, camera_uuid: UUID | None, creator_id: int
) -> int:
    if camera_uuid is not None:
        return _resolve_camera_id(db, camera_uuid)
    return resolve_or_default_camera_id(db, None, creator_id)


@router.get(
    "",
    response_model=DiveListResponse,
    summary="List Dives",
    description="""
Return every dive in the system, ordered by creation time. Requires the scientist role.
""",
)
def list_dives(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Dive, Region, Camera, User)
        .join(Region, Dive.region_id == Region.id)
        .join(Camera, Dive.camera_id == Camera.id)
        .join(User, Dive.created_by == User.id)
        .order_by(Dive.created_at)
    ).all()
    return DiveListResponse(
        dives=[
            DiveResponse(
                uuid=UUID(bytes=dive.uuid),
                created_at=dive.created_at,
                created_by=UUID(bytes=creator.uuid),
                title=dive.title,
                metadata=decode_metadata(dive.metadata_json),
                description=dive.description,
                region=UUID(bytes=region.uuid),
                camera=UUID(bytes=camera.uuid),
            )
            for dive, region, camera, creator in rows
        ]
    )


@router.post(
    "/create",
    response_model=DiveResponse,
    status_code=201,
    summary="Create Dive",
    description="""
Create a new dive, identified by uuid, associated with an existing region and, optionally, an existing camera. Requires the scientist role.

If camera is omitted, the dive is associated with the "Unknown Camera" with the constant uuid "0484f929-b38d-4076-8aea-864e9c2138a2" instead.

Fails with 404 if the region or camera does not exist, or 409 if a dive with this uuid or title already exists.
""",
)
def create_dive(
    payload: DiveCreateRequest, request: Request, db: Session = Depends(get_db)
):
    user = require_current_user(request)

    region_id = _resolve_region_id(db, payload.region)
    camera_id = _resolve_or_default_camera_id(db, payload.camera, user.id)

    try:
        dive = _create_dive_row(
            db,
            uuid=payload.uuid,
            title=payload.title,
            metadata=payload.metadata,
            description=payload.description,
            region_id=region_id,
            camera_id=camera_id,
            creator_id=user.id,
        )
    except ConflictError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Dive already exists")
    db.commit()
    db.refresh(dive)
    return _to_response(dive, db)


@router.post(
    "/update",
    response_model=DiveResponse,
    summary="Update Dive",
    description="""
Partially update an existing dive, identified by uuid. Requires the scientist role.

Only the fields supplied in the request are changed; omitted fields are left as-is. Sending an explicit null for title, region, or camera is a no-op, but sending an explicit null for metadata or description clears it.

If you want to set the camera to unknown, use uuid "0484f929-b38d-4076-8aea-864e9c2138a2" instead of nulling it.

Fails with 404 if the uuid, region, or camera is not found, or 409 if the new title is already taken.
""",
)
def update_dive(
    payload: DiveUpdateRequest, request: Request, db: Session = Depends(get_db)
):
    require_current_user(request)

    dive = get_by_uuid(db, Dive, payload.uuid.bytes)
    if dive is None:
        raise HTTPException(status_code=404, detail="Dive not found")

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
        setattr(dive, column, value)

    if "region" in payload.model_fields_set and payload.region is not None:
        dive.region_id = _resolve_region_id(db, payload.region)
    if "camera" in payload.model_fields_set and payload.camera is not None:
        dive.camera_id = _resolve_camera_id(db, payload.camera)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Dive already exists")
    db.refresh(dive)
    return _to_response(dive, db)
