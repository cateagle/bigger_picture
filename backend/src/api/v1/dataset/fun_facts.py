from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.api.v1.dataset._metadata import decode_metadata, encode_metadata
from src.db import get_db
from src.models.dataset import FunFactCreateRequest, FunFactListResponse, FunFactResponse, FunFactUpdateRequest
from src.schema.fun_facts import FunFact
from src.schema.regions import Region
from src.schema.users import User
from src.services.errors import ConflictError
from src.services.fun_facts import create_fun_fact as _create_fun_fact_row
from src.services.lookups import get_by_uuid
from src.util import apply_partial_update

router = APIRouter()


def _to_response(fun_fact: FunFact, db: Session) -> FunFactResponse:
    creator = db.get(User, fun_fact.created_by)
    region_uuid = None
    if fun_fact.region_id is not None:
        region = db.get(Region, fun_fact.region_id)
        region_uuid = UUID(bytes=region.uuid)
    return FunFactResponse(
        uuid=UUID(bytes=fun_fact.uuid),
        created_at=fun_fact.created_at,
        created_by=UUID(bytes=creator.uuid),
        title=fun_fact.title,
        fact=decode_metadata(fun_fact.fact_json),
        min_level=fun_fact.min_level,
        region=region_uuid,
    )


def _resolve_region_id(db: Session, region_uuid: UUID) -> int:
    region = get_by_uuid(db, Region, region_uuid.bytes)
    if region is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return region.id


@router.get(
    "",
    response_model=FunFactListResponse,
    summary="List Fun Facts",
    description="""
Return a page of every fun fact in the system, ordered by creation time. Requires the scientist role.
""",
)
def list_fun_facts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    total = db.execute(select(func.count()).select_from(FunFact)).scalar_one()
    fun_facts = db.execute(
        select(FunFact).order_by(FunFact.created_at).limit(page_size).offset((page - 1) * page_size)
    ).scalars().all()
    return FunFactListResponse(
        fun_facts=[_to_response(fun_fact, db) for fun_fact in fun_facts], total=total
    )


@router.post(
    "/create",
    response_model=FunFactResponse,
    status_code=201,
    summary="Create Fun Fact",
    description="""
Create a new fun fact, identified by uuid, with the given title, fact payload, and optional min_level and region. Requires the scientist role.

Fails with 404 if region is supplied but does not exist, or 409 if a fun fact with this uuid or title already exists.
""",
)
def create_fun_fact(payload: FunFactCreateRequest, request: Request, db: Session = Depends(get_db)):
    user = require_current_user(request)

    region_id = None
    if payload.region is not None:
        region_id = _resolve_region_id(db, payload.region)

    try:
        fun_fact = _create_fun_fact_row(
            db,
            uuid=payload.uuid,
            title=payload.title,
            fact=payload.fact,
            min_level=payload.min_level,
            region_id=region_id,
            creator_id=user.id,
        )
    except ConflictError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Fun fact already exists")
    db.commit()
    db.refresh(fun_fact)
    return _to_response(fun_fact, db)


@router.post(
    "/update",
    response_model=FunFactResponse,
    summary="Update Fun Fact",
    description="""
Partially update an existing fun fact, identified by uuid. Requires the scientist role.

Only the fields supplied in the request are changed; omitted fields are left as-is. Sending an explicit null for title, fact, or min_level is a no-op, but sending an explicit null for region clears it (applies to all regions).

Fails with 404 if the uuid is not found or region is supplied but does not exist, or 409 if the new title is already taken.
""",
)
def update_fun_fact(payload: FunFactUpdateRequest, request: Request, db: Session = Depends(get_db)):
    require_current_user(request)

    fun_fact = get_by_uuid(db, FunFact, payload.uuid.bytes)
    if fun_fact is None:
        raise HTTPException(status_code=404, detail="Fun fact not found")

    updates: dict[str, Any] = apply_partial_update(
        payload,
        nullable_columns=set(),
        field_map={"title": "title", "fact": "fact_json", "min_level": "min_level"},
    )
    if "fact_json" in updates:
        updates["fact_json"] = encode_metadata(updates["fact_json"])
    for column, value in updates.items():
        setattr(fun_fact, column, value)

    if "region" in payload.model_fields_set:
        if payload.region is None:
            fun_fact.region_id = None
        else:
            fun_fact.region_id = _resolve_region_id(db, payload.region)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Fun fact already exists")
    db.refresh(fun_fact)
    return _to_response(fun_fact, db)
