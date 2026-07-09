"""Daily quests: a fixed catalog, a deterministic per-day selection, and
confirmed-only progress counting.

Everything here is derived, not stored. Progress is a live `COUNT(*)` over the
existing annotation tables, and a day's quest set is recomputed from a seed
rather than persisted. The only thing the caller persists elsewhere is a claim
row, so a completed quest's XP is granted exactly once per (user, quest, day).

Progress deliberately counts only *confirmed* work — annotations that reached
`ANNOTATION_APPROVED` — windowed by `reviewed_at` (the moment of confirmation).
This mirrors the base XP system, which only rewards reviewed-and-approved work,
so quest XP is never earned for unreviewed submissions.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src import config
from src.constants import ANNOTATION_APPROVED
from src.schema.candidate_annotations import CandidateAnnotation
from src.schema.point_annotations import PointAnnotation


@dataclass(frozen=True)
class QuestTemplate:
    key: str
    title: str
    description: str
    metric: str
    target: int
    reward_exp: int


# The pool the daily set is drawn from. Keep `key` values stable — they're
# stored on claim rows and referenced by the claim endpoint.
CATALOG: tuple[QuestTemplate, ...] = (
    QuestTemplate(
        key="pairs_confirmed_10",
        title="Overlap Scout",
        description="Get 10 of your overlap votes confirmed today.",
        metric="pairs_confirmed",
        target=10,
        reward_exp=15,
    ),
    QuestTemplate(
        key="overlaps_confirmed_5",
        title="Match Maker",
        description="Get 5 pairs you judged to overlap confirmed today.",
        metric="overlaps_confirmed",
        target=5,
        reward_exp=15,
    ),
    QuestTemplate(
        key="points_confirmed_50",
        title="Point Master",
        description="Get 50 of your annotated points confirmed today.",
        metric="points_confirmed",
        target=50,
        reward_exp=25,
    ),
    QuestTemplate(
        key="points_confirmed_20",
        title="Steady Hand",
        description="Get 20 of your annotated points confirmed today.",
        metric="points_confirmed",
        target=20,
        reward_exp=12,
    ),
    QuestTemplate(
        key="pairs_annotated_confirmed_5",
        title="Cartographer",
        description="Get 5 image pairs you annotated confirmed today.",
        metric="pairs_annotated_confirmed",
        target=5,
        reward_exp=20,
    ),
    QuestTemplate(
        key="verifications_20",
        title="Quality Control",
        description="Review 20 annotations today.",
        metric="verifications",
        target=20,
        reward_exp=20,
    ),
    QuestTemplate(
        key="verifications_10",
        title="Second Pair of Eyes",
        description="Review 10 annotations today.",
        metric="verifications",
        target=10,
        reward_exp=10,
    ),
)

CATALOG_BY_KEY: dict[str, QuestTemplate] = {q.key: q for q in CATALOG}


def day_window(now_ms: int) -> tuple[int, int]:
    """Return the [start, end) unix-ms bounds of the local day containing `now_ms`.

    Bounds are the local midnights in `config.QUEST_TIMEZONE`. `end` is computed
    via a calendar +1 day (not +24h) so it stays correct across DST changes, and
    `start` doubles as the seed for the day's quest selection.
    """
    tz = ZoneInfo(config.QUEST_TIMEZONE)
    local_now = datetime.fromtimestamp(now_ms / 1000, tz)
    start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def select_daily_quests(day_start_ms: int) -> list[QuestTemplate]:
    """Pick the day's quests from the catalog, seeded only by the day.

    Same seed -> same set and order for every user, so the daily quests are
    global. `user.id` is intentionally not part of the seed.
    """
    rng = random.Random(day_start_ms)
    count = min(config.QUEST_COUNT_PER_DAY, len(CATALOG))
    quests = rng.sample(list(CATALOG), k=count)
    rng.shuffle(quests)
    return quests


def count_progress(db: Session, user_id: int, metric: str, start_ms: int, end_ms: int) -> int:
    """Count the user's confirmed work for `metric` within the [start, end) window.

    "Confirmed" means status `ANNOTATION_APPROVED`, windowed by `reviewed_at`.
    Verifications are the reviewer's own confirmed actions, windowed the same way.
    """
    if metric in ("pairs_confirmed", "overlaps_confirmed"):
        conds = [
            CandidateAnnotation.created_by == user_id,
            CandidateAnnotation.status_id == ANNOTATION_APPROVED,
            CandidateAnnotation.reviewed_at >= start_ms,
            CandidateAnnotation.reviewed_at < end_ms,
        ]
        if metric == "overlaps_confirmed":
            conds.append(CandidateAnnotation.no_overlap.is_(False))
        return db.execute(select(func.count()).select_from(CandidateAnnotation).where(*conds)).scalar_one()

    if metric in ("points_confirmed", "pairs_annotated_confirmed"):
        conds = [
            PointAnnotation.created_by == user_id,
            PointAnnotation.status_id == ANNOTATION_APPROVED,
            PointAnnotation.reviewed_at >= start_ms,
            PointAnnotation.reviewed_at < end_ms,
        ]
        if metric == "pairs_annotated_confirmed":
            return db.execute(
                select(func.count(func.distinct(PointAnnotation.pair_id))).where(*conds)
            ).scalar_one()
        return db.execute(select(func.count()).select_from(PointAnnotation).where(*conds)).scalar_one()

    if metric == "verifications":
        total = 0
        for model in (CandidateAnnotation, PointAnnotation):
            total += db.execute(
                select(func.count())
                .select_from(model)
                .where(
                    model.reviewed_by == user_id,
                    model.reviewed_at >= start_ms,
                    model.reviewed_at < end_ms,
                )
            ).scalar_one()
        return total

    raise ValueError(f"Unknown quest metric: {metric}")
