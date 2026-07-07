from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
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
    uuid: UUID
    scope: str = Field(min_length=1, max_length=127)
    title: str = Field(min_length=1, max_length=127)
    description: str | None = Field(default=None, max_length=1023)


class LabelUpdateRequest(BaseModel):
    uuid: UUID
    scope: str | None = Field(default=None, min_length=1, max_length=127)
    title: str | None = Field(default=None, min_length=1, max_length=127)
    description: str | None = Field(default=None, max_length=1023)


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


@router.post("/create", response_model=LabelResponse, status_code=201)
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


@router.post("/update", response_model=LabelResponse)
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
