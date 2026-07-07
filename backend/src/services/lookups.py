from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.schema.images import Image


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
