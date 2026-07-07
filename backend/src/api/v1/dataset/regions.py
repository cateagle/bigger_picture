from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.api.v1.dataset._metadata import decode_metadata, encode_metadata
from src.db import get_db
from src.models.dataset import RegionResponse
from src.schema.regions import Region
from src.schema.users import User
from src.services.lookups import get_by_uuid
from src.util import apply_partial_update, now_ms

router = APIRouter()


class RegionCreateRequest(BaseModel):
    uuid: UUID
    title: str = Field(min_length=1, max_length=127)
    metadata: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=1023)


class RegionUpdateRequest(BaseModel):
    uuid: UUID
    title: str | None = Field(default=None, min_length=1, max_length=127)
    metadata: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=1023)


def _to_response(region: Region, db: Session) -> RegionResponse:
    creator = db.get(User, region.created_by)
    return RegionResponse(
        uuid=UUID(bytes=region.uuid),
        created_at=region.created_at,
        created_by=UUID(bytes=creator.uuid),
        title=region.title,
        metadata=decode_metadata(region.metadata_json),
        description=region.description,
    )


@router.post("/create", response_model=RegionResponse, status_code=201)
def create_region(payload: RegionCreateRequest, request: Request, db: Session = Depends(get_db)):
    user = require_current_user(request)

    region = Region(
        uuid=payload.uuid.bytes,
        created_at=now_ms(),
        created_by=user.id,
        title=payload.title,
        metadata_json=encode_metadata(payload.metadata),
        description=payload.description,
    )
    db.add(region)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Region already exists")
    db.refresh(region)
    return _to_response(region, db)


@router.post("/update", response_model=RegionResponse)
def update_region(payload: RegionUpdateRequest, request: Request, db: Session = Depends(get_db)):
    require_current_user(request)

    region = get_by_uuid(db, Region, payload.uuid.bytes)
    if region is None:
        raise HTTPException(status_code=404, detail="Region not found")

    updates = apply_partial_update(
        payload,
        nullable_columns={"metadata_json", "description"},
        field_map={"title": "title", "metadata": "metadata_json", "description": "description"},
    )
    if updates.get("metadata_json") is not None:
        updates["metadata_json"] = encode_metadata(updates["metadata_json"])
    for column, value in updates.items():
        setattr(region, column, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Region already exists")
    db.refresh(region)
    return _to_response(region, db)
