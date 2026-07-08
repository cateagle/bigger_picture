from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.api.v1.dataset._metadata import decode_metadata
from src.db import get_db
from src.models.dataset import FunFactResponse
from src.schema.fun_facts import FunFact
from src.schema.regions import Region
from src.schema.seen_facts import SeenFact
from src.schema.users import User
from src.services.lookups import get_by_uuid

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
    "/random",
    response_model=FunFactResponse,
    summary="Get Random Fun Fact",
    description="""
Return a random fun fact eligible for the caller, and record that they've been shown it. Requires the annotator role (or any higher role).

A fun fact is eligible when: it has not been shown to the caller max_seen times yet (seen_count < max_seen, or never shown); its region is null or matches the given region; and its min_level is at most the caller's expert_level.

On a match, the caller's seen count for that fact is inserted at 1 or incremented by 1 if it already exists, in the same request.

Fails with 404 if region is supplied but does not exist, or if no fun fact is currently eligible.
""",
)
def get_random_fun_fact(
    request: Request,
    max_seen: int = Query(ge=0),
    region: UUID | None = None,
    db: Session = Depends(get_db),
):
    user = require_current_user(request)

    region_id = None
    if region is not None:
        region_id = _resolve_region_id(db, region)

    stmt = (
        select(FunFact)
        .outerjoin(
            SeenFact,
            and_(SeenFact.user_id == user.id, SeenFact.fact_id == FunFact.id),
        )
        .where(
            or_(SeenFact.seen_count.is_(None), SeenFact.seen_count < max_seen),
            or_(FunFact.region_id.is_(None), FunFact.region_id == region_id),
            FunFact.min_level <= user.expert_level,
        )
        .order_by(func.random())
        .limit(1)
    )
    fun_fact = db.execute(stmt).scalars().first()
    if fun_fact is None:
        raise HTTPException(status_code=404, detail="No fun fact available")

    upsert = sqlite_insert(SeenFact).values(user_id=user.id, fact_id=fun_fact.id, seen_count=1)
    upsert = upsert.on_conflict_do_update(
        index_elements=[SeenFact.user_id, SeenFact.fact_id],
        set_={"seen_count": SeenFact.seen_count + 1},
    )
    db.execute(upsert)
    db.commit()

    return _to_response(fun_fact, db)
