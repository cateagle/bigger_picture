from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.constants import (
    CANDIDATE_STATUS_INT,
    INT_CANDIDATE_STATUS,
    PAIR_STATUS_INT,
    CandidateStatus,
    PairStatus,
)
from src.db import get_db
from src.models.dataset import CandidatePairResponse, ImagePairRef
from src.schema.candidate_pairs import CandidatePair
from src.schema.image_pairs import ImagePair
from src.schema.images import Image
from src.schema.users import User
from src.services.candidate_pairs import create_candidate_pair as _create_candidate_pair_row
from src.services.errors import ConflictError, SameDiveError
from src.services.lookups import resolve_sorted_image_pair
from src.util import now_ms

router = APIRouter()


def _to_response(pair: CandidatePair, db: Session) -> CandidatePairResponse:
    image_a = db.get(Image, pair.image1_id)
    image_b = db.get(Image, pair.image2_id)
    creator = db.get(User, pair.created_by)
    status = None
    if pair.status_id is not None:
        status_enum = INT_CANDIDATE_STATUS.get(pair.status_id)
        status = str(status_enum) if status_enum is not None else None
    return CandidatePairResponse(
        created_at=pair.created_at,
        created_by=UUID(bytes=creator.uuid),
        image_a=UUID(bytes=image_a.uuid),
        image_b=UUID(bytes=image_b.uuid),
        status=status,
    )


def _resolve_pair_ids(db: Session, image_a: UUID, image_b: UUID) -> tuple[int, int]:
    """Resolve two image uuids to sorted ids, mapping errors to HTTP responses."""
    ids = resolve_sorted_image_pair(db, image_a, image_b)
    if ids is None:
        raise HTTPException(status_code=404, detail="Image not found")
    if ids[0] == ids[1]:
        raise HTTPException(status_code=422, detail="image_a and image_b must differ")
    return ids


@router.post(
    "/create",
    response_model=CandidatePairResponse,
    status_code=201,
    summary="Create Candidate Pair",
    description="""
Create a new candidate pair from two existing images, to be reviewed for overlap. Requires the scientist role. The order of image_a and image_b does not matter and the backend ensures bidirectional uniqueness.

The pair is always created with status "hidden".

Fails with 404 if either image does not exist, 422 if image_a and image_b are the same image or belong to different dives, or 409 if a candidate pair for this image combination already exists.
""",
)
def create_candidate_pair(
    payload: ImagePairRef, request: Request, db: Session = Depends(get_db)
):
    user = require_current_user(request)
    ids = _resolve_pair_ids(db, payload.image_a, payload.image_b)

    try:
        pair = _create_candidate_pair_row(
            db,
            image1_id=ids[0],
            image2_id=ids[1],
            status_id=CANDIDATE_STATUS_INT[CandidateStatus.HIDDEN],
            creator_id=user.id,
        )
    except SameDiveError:
        db.rollback()
        raise HTTPException(status_code=422, detail="Images must belong to the same dive")
    except ConflictError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Candidate pair already exists")
    db.commit()
    db.refresh(pair)
    return _to_response(pair, db)


@router.post(
    "/batch/status-change/{new_status}",
    summary="Batch Change Candidate Pair Status",
    description="""
Set the status of the given candidate pairs, each referenced by its image_a/image_b uuids, to new_status. Requires the scientist role.

Valid statuses are hidden, open, no_overlap, has_overlap, and deleted. Transitioning a pair to has_overlap also creates a corresponding image pair, with status "hidden", for the same image combination, unless one already exists.

Fails with 422 if new_status is not a recognized status, 404 if any item's images or candidate pair cannot be found, or 422 if any item's image_a and image_b are the same image.
""",
)
def batch_status_change(
    new_status: str,
    items: list[ImagePairRef],
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_current_user(request)

    status_id = CANDIDATE_STATUS_INT.get(new_status)
    if status_id is None:
        raise HTTPException(status_code=422, detail="Unknown candidate status")

    # Resolve every item to its existing CandidatePair row before mutating.
    pairs: list[CandidatePair] = []
    for item in items:
        ids = _resolve_pair_ids(db, item.image_a, item.image_b)
        pair = db.execute(
            select(CandidatePair).where(
                CandidatePair.image1_id == ids[0],
                CandidatePair.image2_id == ids[1],
            )
        ).scalar_one_or_none()
        if pair is None:
            raise HTTPException(status_code=404, detail="Candidate pair not found")
        pairs.append(pair)

    for pair in pairs:
        pair.status_id = status_id

    created_image_pairs = 0
    if status_id == CANDIDATE_STATUS_INT[CandidateStatus.HAS_OVERLAP]:
        for pair in pairs:
            # Only insert an ImagePair if one does not already exist for the
            # same (sorted) images, so the UNIQUE(image1,image2) constraint
            # cannot abort this transaction.
            existing = db.execute(
                select(ImagePair).where(
                    ImagePair.image1_id == pair.image1_id,
                    ImagePair.image2_id == pair.image2_id,
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    ImagePair(
                        created_at=now_ms(),
                        created_by=user.id,
                        image1_id=pair.image1_id,
                        image2_id=pair.image2_id,
                        status_id=PAIR_STATUS_INT[PairStatus.HIDDEN],
                    )
                )
                created_image_pairs += 1

    db.commit()
    return {"updated": len(pairs), "image_pairs_created": created_image_pairs}
