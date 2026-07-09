from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.api.v1.dataset._metadata import decode_metadata, encode_metadata
from src.api.v1.dataset.helper_images import helper_image_to_response
from src.db import get_db
from src.models.dataset import FunFactCreateRequest, FunFactListResponse, FunFactResponse, FunFactUpdateRequest
from src.schema.fun_facts import FunFact
from src.schema.helper_images import HelperImage
from src.schema.regions import Region
from src.schema.users import User
from src.services.errors import ConflictError
from src.services.fun_facts import create_fun_fact as _create_fun_fact_row
from src.services.helper_images import get_or_create_helper_image
from src.services.lookups import get_by_uuid
from src.util import apply_partial_update

router = APIRouter()


def _to_response(fun_fact: FunFact, db: Session) -> FunFactResponse:
    creator = db.get(User, fun_fact.created_by)
    region_uuid = None
    if fun_fact.region_id is not None:
        region = db.get(Region, fun_fact.region_id)
        region_uuid = UUID(bytes=region.uuid)
    image_response = None
    if fun_fact.image_id is not None:
        image_response = helper_image_to_response(db.get(HelperImage, fun_fact.image_id), db)
    return FunFactResponse(
        uuid=UUID(bytes=fun_fact.uuid),
        created_at=fun_fact.created_at,
        created_by=UUID(bytes=creator.uuid),
        title=fun_fact.title,
        fact=decode_metadata(fun_fact.fact_json),
        min_level=fun_fact.min_level,
        region=region_uuid,
        image=image_response,
    )


def _resolve_region_id(db: Session, region_uuid: UUID) -> int:
    region = get_by_uuid(db, Region, region_uuid.bytes)
    if region is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return region.id


def _resolve_helper_image_id(db: Session, image_uuid: UUID) -> int:
    helper_image = get_by_uuid(db, HelperImage, image_uuid.bytes)
    if helper_image is None:
        raise HTTPException(status_code=404, detail="Helper image not found")
    return helper_image.id


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
Create a new fun fact, identified by uuid, with the given title, fact payload, and optional min_level, region, and image. Requires the scientist role.

The image may be supplied either as base64-encoded bytes (image + image_filename), which are deduplicated by content into a helper image, or as a reference to an existing helper image (image_uuid). image and image_uuid are mutually exclusive; image_filename is required when image is supplied.

Fails with 404 if region or image_uuid is supplied but does not exist, 422 if image/image_uuid are both supplied, image_filename is missing or extraneous, or the image data cannot be decoded, or 409 if a fun fact with this uuid or title already exists.
""",
)
def create_fun_fact(payload: FunFactCreateRequest, request: Request, db: Session = Depends(get_db)):
    user = require_current_user(request)

    region_id = None
    if payload.region is not None:
        region_id = _resolve_region_id(db, payload.region)

    if payload.image is not None and payload.image_uuid is not None:
        raise HTTPException(status_code=422, detail="image and image_uuid are mutually exclusive")
    if payload.image is not None and payload.image_filename is None:
        raise HTTPException(status_code=422, detail="image_filename is required when image is supplied")
    if payload.image is None and payload.image_filename is not None:
        raise HTTPException(status_code=422, detail="image_filename supplied without image")

    image_id = None
    if payload.image is not None:
        try:
            helper_image = get_or_create_helper_image(
                db, image_b64=payload.image, filename=payload.image_filename, creator_id=user.id,
            )
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid image data")
        image_id = helper_image.id
    elif payload.image_uuid is not None:
        image_id = _resolve_helper_image_id(db, payload.image_uuid)

    try:
        fun_fact = _create_fun_fact_row(
            db,
            uuid=payload.uuid,
            title=payload.title,
            fact=payload.fact,
            min_level=payload.min_level,
            region_id=region_id,
            image_id=image_id,
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

The image has four possible states, at most one of which may be active per request: leave unchanged (omit image, image_uuid, and clear_image), upload new bytes and attach them (image + image_filename), attach an existing helper image (image_uuid), or detach the current image (clear_image: true).

Fails with 404 if the uuid is not found, or region or image_uuid is supplied but does not exist, or 409 if the new title is already taken.
""",
)
def update_fun_fact(payload: FunFactUpdateRequest, request: Request, db: Session = Depends(get_db)):
    user = require_current_user(request)

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

    image_actions_active = sum([
        payload.image is not None,
        payload.image_uuid is not None,
        payload.clear_image,
    ])
    if image_actions_active > 1:
        db.rollback()
        raise HTTPException(
            status_code=422, detail="image, image_uuid, and clear_image are mutually exclusive"
        )
    if payload.image is not None and payload.image_filename is None:
        db.rollback()
        raise HTTPException(status_code=422, detail="image_filename is required when image is supplied")
    if payload.image is None and payload.image_filename is not None:
        db.rollback()
        raise HTTPException(status_code=422, detail="image_filename supplied without image")

    if payload.image is not None:
        try:
            helper_image = get_or_create_helper_image(
                db, image_b64=payload.image, filename=payload.image_filename, creator_id=user.id,
            )
        except ValueError:
            db.rollback()
            raise HTTPException(status_code=422, detail="Invalid image data")
        fun_fact.image_id = helper_image.id
    elif payload.image_uuid is not None:
        fun_fact.image_id = _resolve_helper_image_id(db, payload.image_uuid)
    elif payload.clear_image:
        fun_fact.image_id = None

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Fun fact already exists")
    db.refresh(fun_fact)
    return _to_response(fun_fact, db)
