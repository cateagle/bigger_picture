from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.v1.dataset._metadata import encode_metadata
from src.schema.fun_facts import FunFact
from src.services.errors import ConflictError
from src.util import now_ms


def create_fun_fact(
    db: Session,
    *,
    uuid: UUID,
    title: str,
    fact: Any,
    min_level: int,
    region_id: int | None,
    creator_id: int,
) -> FunFact:
    """Build, add, and flush a new `FunFact` row. Does not commit.

    Raises `ConflictError` if the uuid or title already exists.
    """
    fun_fact = FunFact(
        uuid=uuid.bytes,
        created_at=now_ms(),
        created_by=creator_id,
        title=title,
        fact_json=encode_metadata(fact),
        min_level=min_level,
        region_id=region_id,
    )
    db.add(fun_fact)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError("Fun fact already exists") from exc
    return fun_fact
