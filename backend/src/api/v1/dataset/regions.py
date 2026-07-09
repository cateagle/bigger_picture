from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.api.v1.dataset._metadata import decode_metadata, encode_metadata
from src.db import get_db
from src.models.dataset import RegionResponse
from src.schema.regions import Region
from src.schema.users import User
from src.services.errors import ConflictError
from src.services.lookups import get_by_uuid
from src.services.regions import create_region as _create_region_row
from src.util import apply_partial_update

router = APIRouter()


class RegionCreateRequest(BaseModel):
    """Request used to create a new region."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuid": "8f8b65dc-fbf2-4dfb-bff2-f34072bb97e2",
                "title": "Gulf of Mexico",
                "metadata": None,
                "description": None,
            }
        }
    )

    uuid: UUID = Field(description="Unique identifier to assign to the new region.")

    title: str = Field(
        min_length=1,
        max_length=127,
        description="Display name of the region. Must be unique.",
    )

    metadata: dict[str, Any] | None = Field(
        default=None, description="Arbitrary JSON object to attach to the region."
    )

    description: str | None = Field(
        default=None,
        max_length=1023,
        description="Optional free-text description of the region.",
    )


class RegionUpdateRequest(BaseModel):
    """Request used to partially update an existing region.

    Only the fields explicitly supplied are changed; omitted fields are left
    untouched. Sending an explicit null for title is also a no-op, since it
    is not a nullable column.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuid": "8f8b65dc-fbf2-4dfb-bff2-f34072bb97e2",
                "title": "Baltic Sea (renamed)",
            }
        }
    )

    uuid: UUID = Field(description="Unique identifier of the region to update.")

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


@router.post(
    "/create",
    response_model=RegionResponse,
    status_code=201,
    summary="Create Region",
    description="""
Create a new region, identified by uuid, with the given title and optional metadata and description. Requires the scientist role.

Fails with 409 if a region with this uuid or title already exists.
""",
)
def create_region(
    payload: RegionCreateRequest, request: Request, db: Session = Depends(get_db)
):
    user = require_current_user(request)

    try:
        region = _create_region_row(
            db,
            uuid=payload.uuid,
            title=payload.title,
            metadata=payload.metadata,
            description=payload.description,
            creator_id=user.id,
        )
    except ConflictError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Region already exists")
    db.commit()
    db.refresh(region)
    return _to_response(region, db)


@router.post(
    "/update",
    response_model=RegionResponse,
    summary="Update Region",
    description="""
Partially update an existing region, identified by uuid. Requires the scientist role.

Only the fields supplied in the request are changed; omitted fields are left as-is. Sending an explicit null for title is a no-op, but sending an explicit null for metadata or description clears it.

Fails with 404 if the uuid is not found, or 409 if the new title is already taken.
""",
)
def update_region(
    payload: RegionUpdateRequest, request: Request, db: Session = Depends(get_db)
):
    require_current_user(request)

    region = get_by_uuid(db, Region, payload.uuid.bytes)
    if region is None:
        raise HTTPException(status_code=404, detail="Region not found")

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
        setattr(region, column, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Region already exists")
    db.refresh(region)
    return _to_response(region, db)
