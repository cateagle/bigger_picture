from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.v1.dataset._metadata import encode_metadata
from src.schema.regions import Region
from src.services.errors import ConflictError
from src.util import now_ms


def create_region(
    db: Session,
    *,
    uuid: UUID,
    title: str,
    metadata: Any | None,
    description: str | None,
    creator_id: int,
) -> Region:
    """Build, add, and flush a new `Region` row. Does not commit.

    Raises `ConflictError` if the uuid or title already exists.
    """
    region = Region(
        uuid=uuid.bytes,
        created_at=now_ms(),
        created_by=creator_id,
        title=title,
        metadata_json=encode_metadata(metadata),
        description=description,
    )
    db.add(region)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError("Region already exists") from exc
    return region
