import csv
import io
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
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


@router.get(
    "/export",
    summary="Export Raw Point Annotations as CSV",
    description="""
Export raw point-annotation rows as CSV (one row per annotation, no aggregation/merging), including the user who created each annotation. Requires the scientist role.

Use repeated `dive` query parameters to limit export to one or more dives. If omitted, exports annotations across all dives.
""",
)
def export_point_annotations_csv(
    dive: list[UUID] | None = Query(
        default=None,
        description="Optional repeated dive UUIDs to filter export. If omitted, includes all dives.",
    ),
    db: Session = Depends(get_db),
):
    requested_dive_ids: list[int] | None = None
    if dive:
        dive_rows = db.execute(select(Dive).where(Dive.uuid.in_([d.bytes for d in dive]))).scalars().all()
        if len(dive_rows) != len(set(dive)):
            raise HTTPException(status_code=404, detail="Dive not found")
        requested_dive_ids = [row.id for row in dive_rows]

    image_a = aliased(Image)
    image_b = aliased(Image)

    # Build output rows through explicit joins so the CSV can include user-level context.
    creator = aliased(User)
    reviewer = aliased(User)
    stmt = (
        select(
            PointAnnotation,
            ImagePair,
            image_a,
            image_b,
            Dive,
            Label,
            creator,
            reviewer,
        )
        .join(ImagePair, PointAnnotation.pair_id == ImagePair.id)
        .join(image_a, ImagePair.image1_id == image_a.id)
        .join(image_b, ImagePair.image2_id == image_b.id)
        .join(Dive, image_a.dive_id == Dive.id)
        .join(creator, PointAnnotation.created_by == creator.id)
        .outerjoin(Label, PointAnnotation.label_id == Label.id)
        .outerjoin(reviewer, PointAnnotation.reviewed_by == reviewer.id)
        .where(image_a.dive_id == image_b.dive_id)
        .order_by(Dive.title, image_a.filename, image_b.filename, PointAnnotation.created_at)
    )

    if requested_dive_ids is not None:
        stmt = stmt.where(Dive.id.in_(requested_dive_ids))

    rows = db.execute(stmt).all()

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(
        [
            "annotation_uuid",
            "dive_uuid",
            "dive_title",
            "image_a_uuid",
            "image_a_filename",
            "image_b_uuid",
            "image_b_filename",
            "label_uuid",
            "label_scope",
            "label_title",
            "x1",
            "y1",
            "x2",
            "y2",
            "annotation_expert_level",
            "confidence",
            "status",
            "created_at",
            "created_by_user_uuid",
            "created_by_username",
            "created_by_role",
            "reviewed_at",
            "reviewed_by_user_uuid",
            "reviewed_by_username",
        ]
    )

    for annotation, _pair, image_a_row, image_b_row, dive_row, label_row, creator_row, reviewer_row in rows:
        status_enum = INT_ANNOTATION_STATUS.get(annotation.status_id)
        writer.writerow(
            [
                str(UUID(bytes=annotation.uuid)),
                str(UUID(bytes=dive_row.uuid)),
                dive_row.title,
                str(UUID(bytes=image_a_row.uuid)),
                image_a_row.filename,
                str(UUID(bytes=image_b_row.uuid)),
                image_b_row.filename,
                str(UUID(bytes=label_row.uuid)) if label_row is not None else "",
                label_row.scope if label_row is not None else "",
                label_row.title if label_row is not None else "",
                annotation.x1,
                annotation.y1,
                annotation.x2,
                annotation.y2,
                annotation.expert_level,
                annotation.confidence if annotation.confidence is not None else "",
                str(status_enum) if status_enum is not None else str(annotation.status_id),
                annotation.created_at,
                str(UUID(bytes=creator_row.uuid)),
                creator_row.username,
                creator_row.role,
                annotation.reviewed_at if annotation.reviewed_at is not None else "",
                str(UUID(bytes=reviewer_row.uuid)) if reviewer_row is not None else "",
                reviewer_row.username if reviewer_row is not None else "",
            ]
        )

    csv_buffer.seek(0)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    headers = {
        "Content-Disposition": f'attachment; filename="point_annotations_{timestamp}.csv"'
    }
    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )
