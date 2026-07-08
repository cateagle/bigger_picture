from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.constants import INT_PAIR_STATUS, PAIR_STATUS_INT, PairStatus
from src.db import get_db
from src.models.dataset import ImagePairRef, ImagePairResponse
from src.schema.image_pairs import ImagePair
from src.schema.images import Image
from src.schema.users import User
from src.services.lookups import resolve_sorted_image_pair
from src.util import now_ms

router = APIRouter()


def _to_response(pair: ImagePair, db: Session) -> ImagePairResponse:
    image_a = db.get(Image, pair.image1_id)
    image_b = db.get(Image, pair.image2_id)
    creator = db.get(User, pair.created_by)
    status = None
    if pair.status_id is not None:
        status_enum = INT_PAIR_STATUS.get(pair.status_id)
        status = str(status_enum) if status_enum is not None else None
    return ImagePairResponse(
        created_at=pair.created_at,
        created_by=UUID(bytes=creator.uuid),
        image_a=UUID(bytes=image_a.uuid),
        image_b=UUID(bytes=image_b.uuid),
        difficulty=pair.difficulty,
        priority=pair.priority,
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
    response_model=ImagePairResponse,
    status_code=201,
    summary="Create Image Pair",
    description="""
Create a new image pair from two existing images, available for point annotation once its status is opened. Requires the scientist role.

The order of image_a and image_b does not matter. The backend reorders them and ensures bidirectional uniqueness.

The pair is always created with status "hidden" and null difficulty/priority.

Fails with 404 if either image does not exist, 422 if image_a and image_b are the same image, or 409 if an image pair for this image combination already exists.
""",
)
def create_image_pair(
    payload: ImagePairRef, request: Request, db: Session = Depends(get_db)
):
    user = require_current_user(request)
    ids = _resolve_pair_ids(db, payload.image_a, payload.image_b)

    pair = ImagePair(
        created_at=now_ms(),
        created_by=user.id,
        image1_id=ids[0],
        image2_id=ids[1],
        status_id=PAIR_STATUS_INT[PairStatus.HIDDEN],
    )
    db.add(pair)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Image pair already exists")
    db.refresh(pair)
    return _to_response(pair, db)


@router.post(
    "/batch/status-change/{new_status}",
    summary="Batch Change Image Pair Status",
    description="""
Set the status of the given image pairs, each referenced by its image_a/image_b uuids, to new_status. Requires the scientist role.

The order of image_a and image_b does not matter. The backend reorders them and ensures bidirectional uniqueness.

Valid statuses are hidden, open, review_pending, finalized, and deleted.

Fails with 422 if new_status is not a recognized status, 404 if any item's images or image pair cannot be found, or 422 if any item's image_a and image_b are the same image.
""",
)
def batch_status_change(
    new_status: str,
    items: list[ImagePairRef],
    request: Request,
    db: Session = Depends(get_db),
):
    require_current_user(request)

    status_id = PAIR_STATUS_INT.get(new_status)
    if status_id is None:
        raise HTTPException(status_code=422, detail="Unknown pair status")

    pairs: list[ImagePair] = []
    for item in items:
        ids = _resolve_pair_ids(db, item.image_a, item.image_b)
        pair = db.execute(
            select(ImagePair).where(
                ImagePair.image1_id == ids[0],
                ImagePair.image2_id == ids[1],
            )
        ).scalar_one_or_none()
        if pair is None:
            raise HTTPException(status_code=404, detail="Image pair not found")
        pairs.append(pair)

    for pair in pairs:
        pair.status_id = status_id

    db.commit()
    return {"updated": len(pairs)}
