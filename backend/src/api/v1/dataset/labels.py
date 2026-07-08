from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.db import get_db
from src.models.dataset import LabelResponse
from src.schema.labels import Label
from src.schema.users import User
from src.services.lookups import get_by_uuid
from src.util import apply_partial_update, now_ms

router = APIRouter()


class LabelCreateRequest(BaseModel):
    """Request used to create a new label."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuid": "8f8b65dc-fbf2-4dfb-bff2-f34072bb97e2",
                "scope": "point-annotation",
                "title": "Coral",
                "description": None,
            }
        }
    )

    uuid: UUID = Field(description="Unique identifier to assign to the new label.")

    scope: str = Field(
        min_length=1,
        max_length=127,
        description="Caller-defined namespace for the label. Combined with title, must be unique.",
    )

    title: str = Field(
        min_length=1, max_length=127, description="Display name of the label."
    )

    description: str | None = Field(
        default=None,
        max_length=1023,
        description="Optional free-text description of the label.",
    )


class LabelUpdateRequest(BaseModel):
    """Request used to partially update an existing label.

    Only the fields explicitly supplied are changed; omitted fields are left
    untouched. Sending an explicit null for scope or title is also a no-op,
    since neither is a nullable column.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuid": "8f8b65dc-fbf2-4dfb-bff2-f34072bb97e2",
                "title": "Coral (renamed)",
            }
        }
    )

    uuid: UUID = Field(description="Unique identifier of the label to update.")

    scope: str | None = Field(
        default=None,
        min_length=1,
        max_length=127,
        description="New scope. Omit to leave unchanged.",
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=127,
        description="New display name. Omit to leave unchanged.",
    )

    description: str | None = Field(
        default=None,
        max_length=1023,
        description="New description. Send null to clear it, or omit to leave unchanged.",
    )


def _to_response(label: Label, db: Session) -> LabelResponse:
    creator = db.get(User, label.created_by)
    return LabelResponse(
        uuid=UUID(bytes=label.uuid),
        created_at=label.created_at,
        created_by=UUID(bytes=creator.uuid),
        scope=label.scope,
        title=label.title,
        description=label.description,
    )


@router.post(
    "/create",
    response_model=LabelResponse,
    status_code=201,
    summary="Create Label",
    description="""
Create a new label, identified by uuid, with the given scope, title, and optional description. Requires the scientist role.

Fails with 409 if a label with this uuid already exists, or if the scope and title combination is already taken.
""",
)
def create_label(payload: LabelCreateRequest, request: Request, db: Session = Depends(get_db)):
    user = require_current_user(request)

    label = Label(
        uuid=payload.uuid.bytes,
        created_at=now_ms(),
        created_by=user.id,
        scope=payload.scope,
        title=payload.title,
        description=payload.description,
    )
    db.add(label)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Label already exists")
    db.refresh(label)
    return _to_response(label, db)


@router.post(
    "/update",
    response_model=LabelResponse,
    summary="Update Label",
    description="""
Partially update an existing label, identified by uuid. Requires the scientist role.

Only the fields supplied in the request are changed; omitted fields are left as-is. Sending an explicit null for scope or title is also a no-op.

Fails with 404 if the uuid is not found, or 409 if the new scope and title combination is already taken.
""",
)
def update_label(payload: LabelUpdateRequest, request: Request, db: Session = Depends(get_db)):
    require_current_user(request)

    label = get_by_uuid(db, Label, payload.uuid.bytes)
    if label is None:
        raise HTTPException(status_code=404, detail="Label not found")

    updates = apply_partial_update(
        payload,
        nullable_columns={"description"},
        field_map={"scope": "scope", "title": "title", "description": "description"},
    )
    for column, value in updates.items():
        setattr(label, column, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Label already exists")
    db.refresh(label)
    return _to_response(label, db)
