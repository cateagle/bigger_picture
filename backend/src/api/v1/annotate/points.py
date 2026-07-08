from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from src import config
from src.api.deps import require_current_user
from src.api.v1.dataset._metadata import decode_metadata
from src.constants import (
    ANNOTATION_APPROVED,
    ANNOTATION_REVIEW_FAILED,
    ANNOTATION_REVIEW_PENDING,
    INT_ANNOTATION_STATUS,
    INT_IMAGE_STATUS,
    INT_PAIR_STATUS,
    PAIR_STATUS_INT,
    PairStatus,
    Role,
)
from src.db import get_db
from src.models.annotate import (
    NextPairImageResponse,
    NextPairResponse,
    PointAnnotationCorrectionRequest,
    PointAnnotationCreateRequest,
    PointAnnotationResponse,
    PointAnnotationReviewResponse,
)
from src.schema.dives import Dive
from src.schema.image_pairs import ImagePair
from src.schema.images import Image
from src.schema.labels import Label
from src.schema.point_annotations import PointAnnotation
from src.schema.users import User
from src.services.experience import grant_exp
from src.services.lookups import get_by_uuid, resolve_sorted_image_pair
from src.util import now_ms

router = APIRouter()

PAIR_OPEN = PAIR_STATUS_INT[PairStatus.OPEN]


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
        status=str(status_enum)
        if status_enum is not None
        else str(annotation.status_id),
        created_at=annotation.created_at,
        created_by=UUID(bytes=creator.uuid),
        reviewed_at=annotation.reviewed_at,
        reviewed_by=reviewed_by,
    )


def _resolve_open_pair(db: Session, image_a: UUID, image_b: UUID) -> ImagePair:
    """Resolve the open ImagePair for two image uuids, mapping errors to HTTP."""
    ids = resolve_sorted_image_pair(db, image_a, image_b)
    if ids is None:
        raise HTTPException(status_code=404, detail="Image not found")
    pair = db.execute(
        select(ImagePair).where(
            ImagePair.image1_id == ids[0],
            ImagePair.image2_id == ids[1],
        )
    ).scalar_one_or_none()
    if pair is None:
        raise HTTPException(status_code=404, detail="Image pair not found")
    if pair.status_id != PAIR_OPEN:
        raise HTTPException(status_code=409, detail="Image pair not open")
    return pair


def _resolve_label_id(db: Session, label_uuid: UUID) -> int:
    """Resolve a label uuid to its id, mapping errors to HTTP responses."""
    label = get_by_uuid(db, Label, label_uuid.bytes)
    if label is None:
        raise HTTPException(status_code=404, detail="Label not found")
    return label.id


def _build_annotation(
    payload: PointAnnotationCreateRequest, user: User, pair: ImagePair, db: Session
) -> PointAnnotation:
    label_id = None
    if "label_id" in payload.model_fields_set and payload.label_id is not None:
        label_id = _resolve_label_id(db, payload.label_id)
    return PointAnnotation(
        uuid=payload.uuid.bytes,
        created_at=now_ms(),
        created_by=user.id,
        pair_id=pair.id,
        label_id=label_id,
        x1=payload.x1,
        y1=payload.y1,
        x2=payload.x2,
        y2=payload.y2,
        expert_level=user.expert_level,
        confidence=None,
        status_id=ANNOTATION_REVIEW_PENDING,
    )


@router.post(
    "/create",
    response_model=PointAnnotationResponse,
    status_code=201,
    summary="Create Point Annotation",
    description="""
Create a new point annotation, identified by uuid, for an open image pair. Requires the annotator role (or any higher role).

expert_level is copied from the caller at creation time; confidence is always null on creation.

Fails with 404 if either image, the image pair, or the given label does not exist, 409 if the image pair is not open, or 409 if the uuid is already used by an existing annotation.
""",
)
def create_annotation(
    payload: PointAnnotationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_current_user(request)
    pair = _resolve_open_pair(db, payload.image_a, payload.image_b)
    annotation = _build_annotation(payload, user, pair, db)
    db.add(annotation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Annotation already exists")
    db.refresh(annotation)
    return _to_response(annotation, db)


@router.post(
    "/batch/create",
    summary="Batch Create Point Annotations",
    description="""
Create multiple point annotations in one request, one per item, using the same rules as Create Point Annotation. Requires the annotator role (or any higher role).

The batch is all-or-nothing: if any item fails validation, or any uuid collides with an existing annotation, none of the items are created.

Fails with 404 if any item's images, image pair, or label do not exist, 409 if any item's image pair is not open, or 409 if any item's uuid is already used by an existing annotation.
""",
)
def batch_create_annotations(
    items: list[PointAnnotationCreateRequest],
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_current_user(request)

    annotations: list[PointAnnotation] = []
    for item in items:
        pair = _resolve_open_pair(db, item.image_a, item.image_b)
        annotation = _build_annotation(item, user, pair, db)
        db.add(annotation)
        annotations.append(annotation)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Annotation already exists")

    db.commit()
    return {"created": len(annotations)}


@router.post(
    "/correction",
    response_model=PointAnnotationResponse,
    summary="Correct a Point Annotation",
    description="""
Update the bounding box and optionally the label of an existing annotation. Can only be done by the user who created the annotation within the first hour of creating the annotation and as long as it is in status "review_pending".

Coordinates are expressed in image pixels. Only the supplied fields are modified.
""",
)
def correct_annotation(
    payload: PointAnnotationCorrectionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_current_user(request)

    annotation = db.execute(
        select(PointAnnotation).where(PointAnnotation.uuid == payload.uuid.bytes)
    ).scalar_one_or_none()
    if annotation is None:
        raise HTTPException(status_code=404, detail="Annotation not found")

    if annotation.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not the annotation creator")
    if annotation.status_id != ANNOTATION_REVIEW_PENDING:
        raise HTTPException(status_code=409, detail="Annotation is not pending review")
    if now_ms() - annotation.created_at >= config.SELF_CORRECTION_TIME_LIMIT_MS:
        raise HTTPException(status_code=403, detail="Correction window expired")

    annotation.x1 = payload.x1
    annotation.y1 = payload.y1
    annotation.x2 = payload.x2
    annotation.y2 = payload.y2
    if "label_id" in payload.model_fields_set:
        if payload.label_id is None:
            annotation.label_id = None
        else:
            annotation.label_id = _resolve_label_id(db, payload.label_id)

    db.commit()
    db.refresh(annotation)
    return _to_response(annotation, db)


def _load_pending_for_review(db: Session, annotation_uuid: UUID) -> PointAnnotation:
    annotation = db.execute(
        select(PointAnnotation).where(PointAnnotation.uuid == annotation_uuid.bytes)
    ).scalar_one_or_none()
    if annotation is None:
        raise HTTPException(status_code=404, detail="Annotation not found")
    if annotation.status_id != ANNOTATION_REVIEW_PENDING:
        raise HTTPException(status_code=409, detail="Annotation is not pending review")
    return annotation


def _authorize_review(caller: User, annotation: PointAnnotation) -> None:
    allowed = (caller.id != annotation.created_by) and (
        (
            caller.expert_level >= config.MIN_REVIEW_EXPERT_LEVEL
            and caller.expert_level > annotation.expert_level
        )
        or caller.role in (Role.SCIENTIST, Role.ADMIN)
    )
    if not allowed:
        raise HTTPException(
            status_code=403, detail="Not authorized to review this annotation"
        )


def _apply_review(
    annotation: PointAnnotation, caller: User, status_id: int, db: Session
) -> PointAnnotationResponse:
    annotation.status_id = status_id
    annotation.reviewed_by = caller.id
    annotation.reviewed_at = now_ms()
    grant_exp(db, db.get(User, caller.id), config.POINT_ANNOTATION_REVIEW_EXP)
    if status_id == ANNOTATION_APPROVED:
        creator = db.get(User, annotation.created_by)
        grant_exp(db, creator, config.POINT_ANNOTATION_REVIEW_EXP)
    db.commit()
    db.refresh(annotation)
    return _to_response(annotation, db)


def _to_review_response(annotation: PointAnnotation, db: Session) -> PointAnnotationReviewResponse:
    pair = db.get(ImagePair, annotation.pair_id)
    image_a = db.get(Image, pair.image1_id)
    image_b = db.get(Image, pair.image2_id)
    label_uuid = None
    if annotation.label_id is not None:
        label = db.get(Label, annotation.label_id)
        if label is not None:
            label_uuid = UUID(bytes=label.uuid)
    status_enum = INT_ANNOTATION_STATUS.get(annotation.status_id)
    return PointAnnotationReviewResponse(
        uuid=UUID(bytes=annotation.uuid),
        image_a=_to_next_image_response(image_a, db),
        image_b=_to_next_image_response(image_b, db),
        label_id=label_uuid,
        x1=annotation.x1,
        y1=annotation.y1,
        x2=annotation.x2,
        y2=annotation.y2,
        expert_level=annotation.expert_level,
        status=str(status_enum) if status_enum is not None else str(annotation.status_id),
        created_at=annotation.created_at,
    )


@router.get(
    "/review/next/{dive_uuid}",
    response_model=list[PointAnnotationReviewResponse],
    summary="Get Next Point Annotations to Review",
    description="""
Return up to n point annotations from the given dive that are pending review and were not created by the caller, with full image details for rendering. Requires the annotator role (or any higher role).

The caller must either hold the scientist or admin role, or have an expert_level that meets the configured minimum and is strictly greater than an annotation's expert_level for that annotation to be eligible; callers who satisfy neither condition always get an empty list. Results are ordered by the parent pair's priority descending (nulls last), then by the annotation's creation time ascending. n defaults to 1 and must be at least 1; there is no upper bound.

Fails with 404 if the dive does not exist, or 422 if n is less than 1.
""",
)
@router.get(
    "/review/next/{dive_uuid}/{n}",
    response_model=list[PointAnnotationReviewResponse],
    summary="Get Next Point Annotations to Review",
    description="""
Return up to n point annotations from the given dive that are pending review and were not created by the caller, with full image details for rendering. Requires the annotator role (or any higher role).

The caller must either hold the scientist or admin role, or have an expert_level that meets the configured minimum and is strictly greater than an annotation's expert_level for that annotation to be eligible; callers who satisfy neither condition always get an empty list. Results are ordered by the parent pair's priority descending (nulls last), then by the annotation's creation time ascending. n defaults to 1 and must be at least 1; there is no upper bound.

Fails with 404 if the dive does not exist, or 422 if n is less than 1.
""",
)
def get_next_reviews(
    dive_uuid: UUID, request: Request, n: int = 1, db: Session = Depends(get_db)
):
    user = require_current_user(request)
    if n < 1:
        raise HTTPException(status_code=422, detail="n must be >= 1")

    dive = get_by_uuid(db, Dive, dive_uuid.bytes)
    if dive is None:
        raise HTTPException(status_code=404, detail="Dive not found")

    is_privileged = user.role in (Role.SCIENTIST, Role.ADMIN)
    if not is_privileged and user.expert_level < config.MIN_REVIEW_EXPERT_LEVEL:
        return []

    Image1 = aliased(Image)
    Image2 = aliased(Image)

    conditions = [
        PointAnnotation.status_id == ANNOTATION_REVIEW_PENDING,
        PointAnnotation.created_by != user.id,
        Image1.dive_id == dive.id,
        Image2.dive_id == dive.id,
    ]
    if not is_privileged:
        conditions.append(PointAnnotation.expert_level < user.expert_level)

    stmt = (
        select(PointAnnotation)
        .join(ImagePair, PointAnnotation.pair_id == ImagePair.id)
        .join(Image1, ImagePair.image1_id == Image1.id)
        .join(Image2, ImagePair.image2_id == Image2.id)
        .where(*conditions)
        .order_by(ImagePair.priority.desc().nullslast(), PointAnnotation.created_at.asc())
        .limit(n)
    )
    annotations = db.execute(stmt).scalars().all()
    return [_to_review_response(annotation, db) for annotation in annotations]


@router.post(
    "/review/{annotation_uuid}/fail",
    response_model=PointAnnotationResponse,
    summary="Fail Point Annotation Review",
    description="""
Mark a pending point annotation as review_failed. Requires the annotator role (or any higher role); the caller cannot review their own annotation.

The caller must either hold the scientist or admin role, or have an expert_level that meets the configured minimum and is strictly greater than the annotation's expert_level.

Fails with 404 if the annotation does not exist, 409 if it is not pending review, or 403 if the caller is not authorized to review it.
""",
)
def review_fail(annotation_uuid: UUID, request: Request, db: Session = Depends(get_db)):
    caller = require_current_user(request)
    annotation = _load_pending_for_review(db, annotation_uuid)
    _authorize_review(caller, annotation)
    return _apply_review(annotation, caller, ANNOTATION_REVIEW_FAILED, db)


@router.post(
    "/review/{annotation_uuid}/approve",
    response_model=PointAnnotationResponse,
    summary="Approve Point Annotation Review",
    description="""
Mark a pending point annotation as approved. Requires the annotator role (or any higher role); the caller cannot review their own annotation.

The caller must either hold the scientist or admin role, or have an expert_level that meets the configured minimum and is strictly greater than the annotation's expert_level.

Fails with 404 if the annotation does not exist, 409 if it is not pending review, or 403 if the caller is not authorized to review it.
""",
)
def review_approve(
    annotation_uuid: UUID, request: Request, db: Session = Depends(get_db)
):
    caller = require_current_user(request)
    annotation = _load_pending_for_review(db, annotation_uuid)
    _authorize_review(caller, annotation)
    return _apply_review(annotation, caller, ANNOTATION_APPROVED, db)


def _to_next_image_response(image: Image, db: Session) -> NextPairImageResponse:
    dive = db.get(Dive, image.dive_id)
    status_enum = INT_IMAGE_STATUS.get(image.status_id)
    return NextPairImageResponse(
        uuid=UUID(bytes=image.uuid),
        filename=image.filename,
        filepath=image.filepath,
        dive_id=UUID(bytes=dive.uuid),
        status=str(status_enum) if status_enum is not None else None,
        size_x=image.size_x,
        size_y=image.size_y,
        metadata=decode_metadata(image.metadata_json),
    )


def _to_next_pair_response(pair: ImagePair, db: Session) -> NextPairResponse:
    image1 = db.get(Image, pair.image1_id)
    image2 = db.get(Image, pair.image2_id)
    status_enum = INT_PAIR_STATUS.get(pair.status_id)
    return NextPairResponse(
        image1=_to_next_image_response(image1, db),
        image2=_to_next_image_response(image2, db),
        difficulty=pair.difficulty,
        priority=pair.priority,
        status=str(status_enum) if status_enum is not None else None,
    )


@router.get(
    "/next/{dive_uuid}",
    response_model=list[NextPairResponse],
    summary="Get Next Point Annotation Pairs",
    description="""
Return up to n open image pairs from the given dive that the caller has not yet annotated. Requires the annotator role (or any higher role).

A pair is only returned if its difficulty is null or at most the caller's expert_level. Results are ordered by priority descending (nulls last), then by creation time ascending. n defaults to 1 and must be at least 1; there is no upper bound.

Fails with 404 if the dive does not exist, or 422 if n is less than 1.
""",
)
@router.get(
    "/next/{dive_uuid}/{n}",
    response_model=list[NextPairResponse],
    summary="Get Next Point Annotation Pairs",
    description="""
Return up to n open image pairs from the given dive that the caller has not yet annotated. Requires the annotator role (or any higher role).

A pair is only returned if its difficulty is null or at most the caller's expert_level. Results are ordered by priority descending (nulls last), then by creation time ascending. n defaults to 1 and must be at least 1; there is no upper bound.

Fails with 404 if the dive does not exist, or 422 if n is less than 1.
""",
)
def get_next_pairs(
    dive_uuid: UUID, request: Request, n: int = 1, db: Session = Depends(get_db)
):
    user = require_current_user(request)
    if n < 1:
        raise HTTPException(status_code=422, detail="n must be >= 1")

    dive = get_by_uuid(db, Dive, dive_uuid.bytes)
    if dive is None:
        raise HTTPException(status_code=404, detail="Dive not found")

    Image1 = aliased(Image)
    Image2 = aliased(Image)
    annotated_pair_ids = select(PointAnnotation.pair_id).where(
        PointAnnotation.created_by == user.id
    )

    stmt = (
        select(ImagePair)
        .join(Image1, ImagePair.image1_id == Image1.id)
        .join(Image2, ImagePair.image2_id == Image2.id)
        .where(
            ImagePair.status_id == PAIR_OPEN,
            Image1.dive_id == dive.id,
            Image2.dive_id == dive.id,
            or_(
                ImagePair.difficulty.is_(None),
                ImagePair.difficulty <= user.expert_level,
            ),
            ImagePair.id.notin_(annotated_pair_ids),
        )
        .order_by(ImagePair.priority.desc().nullslast(), ImagePair.created_at.asc())
        .limit(n)
    )
    pairs = db.execute(stmt).scalars().all()
    return [_to_next_pair_response(pair, db) for pair in pairs]
