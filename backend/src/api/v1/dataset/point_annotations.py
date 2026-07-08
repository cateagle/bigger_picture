from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from src.constants import INT_ANNOTATION_STATUS
from src.db import get_db
from src.models.annotate import PointAnnotationListResponse, PointAnnotationResponse
from src.schema.dives import Dive
from src.schema.image_pairs import ImagePair
from src.schema.images import Image
from src.schema.labels import Label
from src.schema.point_annotations import PointAnnotation
from src.schema.users import User
from src.services.lookups import get_by_uuid

router = APIRouter()


def _to_response(annotation: PointAnnotation, db: Session) -> PointAnnotationResponse:
    pair = db.get(ImagePair, annotation.pair_id)
    image_a = db.get(Image, pair.image1_id)
    image_b = db.get(Image, pair.image2_id)
    label_uuid = None
    if annotation.label_id is not None:
        label = db.get(Label, annotation.label_id)
        if label is not None:
            label_uuid = UUID(bytes=label.uuid)
    status_enum = INT_ANNOTATION_STATUS.get(annotation.status_id)
    creator = db.get(User, annotation.created_by)
    reviewed_by = None
    if annotation.reviewed_by is not None:
        reviewer = db.get(User, annotation.reviewed_by)
        reviewed_by = UUID(bytes=reviewer.uuid)
    return PointAnnotationResponse(
        uuid=UUID(bytes=annotation.uuid),
        image_a=UUID(bytes=image_a.uuid),
        image_b=UUID(bytes=image_b.uuid),
        label_id=label_uuid,
        x1=annotation.x1,
        y1=annotation.y1,
        x2=annotation.x2,
        y2=annotation.y2,
        expert_level=annotation.expert_level,
        confidence=annotation.confidence,
        status=str(status_enum) if status_enum is not None else str(annotation.status_id),
        created_at=annotation.created_at,
        created_by=UUID(bytes=creator.uuid),
        reviewed_at=annotation.reviewed_at,
        reviewed_by=reviewed_by,
    )


@router.get(
    "",
    response_model=PointAnnotationListResponse,
    summary="List Point Annotations In Dive",
    description="""
Return the point annotations whose image pair's images both belong to the given dive, across all statuses (review_pending, review_failed, and approved), ordered by creation time. Requires the scientist role.

Fails with 404 if the dive does not exist.
""",
)
def list_point_annotations(dive: UUID, db: Session = Depends(get_db)):
    dive_row = get_by_uuid(db, Dive, dive.bytes)
    if dive_row is None:
        raise HTTPException(status_code=404, detail="Dive not found")

    Image1 = aliased(Image)
    Image2 = aliased(Image)
    annotations = db.execute(
        select(PointAnnotation)
        .join(ImagePair, PointAnnotation.pair_id == ImagePair.id)
        .join(Image1, ImagePair.image1_id == Image1.id)
        .join(Image2, ImagePair.image2_id == Image2.id)
        .where(Image1.dive_id == dive_row.id, Image2.dive_id == dive_row.id)
        .order_by(PointAnnotation.created_at)
    ).scalars().all()
    return PointAnnotationListResponse(annotations=[_to_response(a, db) for a in annotations])
