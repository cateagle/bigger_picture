from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.db import get_db
from src.models.annotate import DailyQuestsResponse, QuestClaimResponse, QuestResponse
from src.schema.quest_claims import QuestClaim
from src.schema.users import User
from src.services.experience import grant_exp
from src.services.quests import (
    CATALOG_BY_KEY,
    count_progress,
    day_window,
    select_daily_quests,
)
from src.util import now_ms

router = APIRouter()


def _claimed_keys(db: Session, user_id: int, day_start_ms: int) -> set[str]:
    rows = db.execute(
        select(QuestClaim.quest_key).where(
            QuestClaim.user_id == user_id,
            QuestClaim.day_start_ms == day_start_ms,
        )
    ).scalars()
    return set(rows)


def _quest_response(db: Session, user_id: int, template, start_ms: int, end_ms: int, claimed: bool) -> QuestResponse:
    progress = count_progress(db, user_id, template.metric, start_ms, end_ms)
    return QuestResponse(
        key=template.key,
        title=template.title,
        description=template.description,
        metric=template.metric,
        target=template.target,
        progress=min(progress, template.target),
        completed=progress >= template.target,
        claimed=claimed,
        reward_exp=template.reward_exp,
    )


@router.get(
    "/me",
    response_model=DailyQuestsResponse,
    summary="Get My Daily Quests",
    description="""
Return today's daily quests for the signed-in player, with their progress toward each. Requires the annotator role (or any higher role).

The quest set (and its order) is the same for every player on a given day; it rotates daily. Progress counts only the player's *confirmed* work — annotations reviewed and approved today — so freshly submitted but unreviewed work does not advance a quest until it is reviewed. "Today" is a local-midnight-to-midnight window in the server's configured quest timezone.
""",
)
def get_my_quests(request: Request, db: Session = Depends(get_db)):
    user = require_current_user(request)
    start_ms, end_ms = day_window(now_ms())
    claimed = _claimed_keys(db, user.id, start_ms)
    quests = [
        _quest_response(db, user.id, template, start_ms, end_ms, template.key in claimed)
        for template in select_daily_quests(start_ms)
    ]
    return DailyQuestsResponse(day_start_ms=start_ms, quests=quests)


@router.post(
    "/{quest_key}/claim",
    response_model=QuestClaimResponse,
    summary="Claim A Daily Quest Reward",
    description="""
Claim the XP reward for a completed daily quest. Requires the annotator role (or any higher role).

Only succeeds when the quest is part of today's set and the player's confirmed progress has reached its target; the reward is granted at most once per player per quest per day. Because progress counts only confirmed work, XP is never granted for unreviewed submissions.

Fails with 404 if the quest is not in today's set, and 409 if it is not yet completed or was already claimed today.
""",
)
def claim_quest(quest_key: str, request: Request, db: Session = Depends(get_db)):
    caller = require_current_user(request)
    start_ms, end_ms = day_window(now_ms())

    template = CATALOG_BY_KEY.get(quest_key)
    if template is None or template not in select_daily_quests(start_ms):
        raise HTTPException(status_code=404, detail="Quest is not part of today's quests")

    progress = count_progress(db, caller.id, template.metric, start_ms, end_ms)
    if progress < template.target:
        raise HTTPException(status_code=409, detail="Quest is not completed yet")

    user = db.get(User, caller.id)
    db.add(
        QuestClaim(
            user_id=user.id,
            quest_key=template.key,
            day_start_ms=start_ms,
            reward_exp=template.reward_exp,
            created_at=now_ms(),
        )
    )
    grant_exp(db, user, template.reward_exp)
    try:
        db.commit()
    except IntegrityError:
        # Unique (user, quest, day) guards a double-claim (e.g. concurrent request).
        db.rollback()
        raise HTTPException(status_code=409, detail="Quest reward already claimed today")
    db.refresh(user)

    quest = QuestResponse(
        key=template.key,
        title=template.title,
        description=template.description,
        metric=template.metric,
        target=template.target,
        progress=min(progress, template.target),
        completed=True,
        claimed=True,
        reward_exp=template.reward_exp,
    )
    return QuestClaimResponse(quest=quest, exp=user.exp, expert_level=user.expert_level)
