from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.schema.image_pairs import ImagePair
from src.schema.images import Image
from src.schema.point_annotations import PointAnnotation


def get_by_uuid(session: Session, model, uuid_bytes: bytes):
    """Return the `model` row whose `uuid` matches `uuid_bytes`, or None."""
    return session.execute(select(model).where(model.uuid == uuid_bytes)).scalar_one_or_none()


def resolve_image_id(session: Session, image_uuid: UUID) -> int | None:
    """Resolve an image uuid to its integer `id`, or None if unknown."""
    image = get_by_uuid(session, Image, image_uuid.bytes)
    if image is None:
        return None
    return image.id


def resolve_sorted_image_pair(session: Session, image_a: UUID, image_b: UUID) -> tuple[int, int] | None:
    """Resolve two image uuids to their ids, sorted ascending.

    Returns `(image1_id, image2_id)` with `image1_id < image2_id`, or None if
    either image uuid is unknown.
    """
    id_a = resolve_image_id(session, image_a)
    id_b = resolve_image_id(session, image_b)
    if id_a is None or id_b is None:
        return None
    lo, hi = sorted((id_a, id_b))
    return (lo, hi)


def image_has_point_annotations(session: Session, image_id: int) -> bool:
    """True if any point annotation exists on a pair involving `image_id`.

    A point annotation is "for this image" when its pair's `image1_id` or
    `image2_id` equals `image_id`. Uses a single EXISTS/JOIN query.
    """
    stmt = (
        select(PointAnnotation.id)
        .join(ImagePair, PointAnnotation.pair_id == ImagePair.id)
        .where(or_(ImagePair.image1_id == image_id, ImagePair.image2_id == image_id))
        .limit(1)
    )
    return session.execute(stmt).first() is not None
