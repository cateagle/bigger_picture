from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.annotate import LeaderboardEntry, LeaderboardResponse
from src.schema.users import User

router = APIRouter()


@router.get(
    "",
    response_model=LeaderboardResponse,
    summary="Get Leaderboard",
    description="""
Return a page of the global leaderboard, ranking every player by total experience points, highest first. Requires the annotator role (or any higher role).

Paginate with `limit`/`offset`: request 50 at a time and increment `offset` to load further pages. `total` reports how many players exist so a client knows when it has reached the end. Ties in exp are broken by account age (older accounts rank higher), giving a stable order across pages.
""",
)
def get_leaderboard(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    total = db.execute(select(func.count()).select_from(User)).scalar_one()
    rows = db.execute(
        select(User.uuid, User.username, User.exp)
        .order_by(User.exp.desc(), User.id.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    entries = [
        LeaderboardEntry(
            rank=offset + index + 1,
            uuid=UUID(bytes=row.uuid),
            username=row.username,
            exp=row.exp,
        )
        for index, row in enumerate(rows)
    ]
    return LeaderboardResponse(entries=entries, total=total)
