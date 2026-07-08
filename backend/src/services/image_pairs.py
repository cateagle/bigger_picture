from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.schema.image_pairs import ImagePair
from src.services.errors import ConflictError
from src.services.lookups import require_same_dive
from src.util import now_ms


def create_image_pair(
    db: Session,
    *,
    image1_id: int,
    image2_id: int,
    status_id: int,
    creator_id: int,
) -> ImagePair:
    """Build, add, and flush a new `ImagePair` row. Does not commit.

    `image1_id`/`image2_id` must already be sorted ascending. Raises
    `SameDiveError` if the two images belong to different dives, or
    `ConflictError` if an image pair for this image combination already
    exists. Always created with null difficulty/priority.
    """
    require_same_dive(db, image1_id, image2_id)

    pair = ImagePair(
        created_at=now_ms(),
        created_by=creator_id,
        image1_id=image1_id,
        image2_id=image2_id,
        status_id=status_id,
    )
    db.add(pair)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError("Image pair already exists") from exc
    return pair
