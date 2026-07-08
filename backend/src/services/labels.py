from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.schema.labels import Label
from src.services.errors import ConflictError
from src.util import now_ms


def create_label(
    db: Session,
    *,
    uuid: UUID,
    scope: str,
    title: str,
    description: str | None,
    creator_id: int,
) -> Label:
    """Build, add, and flush a new `Label` row. Does not commit.

    Raises `ConflictError` if the uuid already exists, or the (scope, title)
    combination is already taken.
    """
    label = Label(
        uuid=uuid.bytes,
        created_at=now_ms(),
        created_by=creator_id,
        scope=scope,
        title=title,
        description=description,
    )
    db.add(label)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError("Label already exists") from exc
    return label
