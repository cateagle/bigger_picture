from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from src import config
from src.api.deps import require_current_user
from src.api.v1.dataset._metadata import decode_metadata
from src.constants import (
    ANNOTATION_STATUS_INT,
    CANDIDATE_STATUS_INT,
    INT_ANNOTATION_STATUS,
    INT_CANDIDATE_STATUS,
    INT_IMAGE_STATUS,
    AnnotationStatus,
    CandidateStatus,
    Role,
)
from src.db import get_db
from src.models.annotate import (
    CandidateAnnotationCorrectionRequest,
    CandidateAnnotationCreateRequest,
    CandidateAnnotationResponse,
    NextCandidateResponse,
    NextPairImageResponse,
)
from src.schema.candidate_annotations import CandidateAnnotation
from src.schema.candidate_pairs import CandidatePair
from src.schema.dives import Dive
from src.schema.images import Image
from src.schema.users import User
from src.services.lookups import get_by_uuid, resolve_sorted_image_pair
from src.util import now_ms

router = APIRouter()

STATUS_REVIEW_PENDING = ANNOTATION_STATUS_INT[AnnotationStatus.REVIEW_PENDING]
STATUS_REVIEW_FAILED = ANNOTATION_STATUS_INT[AnnotationStatus.REVIEW_FAILED]
STATUS_APPROVED = ANNOTATION_STATUS_INT[AnnotationStatus.APPROVED]
CANDIDATE_OPEN = CANDIDATE_STATUS_INT[CandidateStatus.OPEN]


def _to_response(annotation: CandidateAnnotation, db: Session) -> CandidateAnnotationResponse:
    candidate = db.get(CandidatePair, annotation.candidate_id)
    image_a = db.get(Image, candidate.image1_id)
    image_b = db.get(Image, candidate.image2_id)
    status_enum = INT_ANNOTATION_STATUS.get(annotation.status_id)
    creator = db.get(User, annotation.created_by)
    reviewed_by = None
    if annotation.reviewed_by is not None:
        reviewer = db.get(User, annotation.reviewed_by)
        reviewed_by = UUID(bytes=reviewer.uuid)
    return CandidateAnnotationResponse(
        uuid=UUID(bytes=annotation.uuid),
        image_a=UUID(bytes=image_a.uuid),
        image_b=UUID(bytes=image_b.uuid),
        no_overlap=annotation.no_overlap,
        expert_level=annotation.expert_level,
        status=str(status_enum) if status_enum is not None else str(annotation.status_id),
        created_at=annotation.created_at,
        created_by=UUID(bytes=creator.uuid),
        reviewed_at=annotation.reviewed_at,
        reviewed_by=reviewed_by,
    )


def _resolve_open_candidate(db: Session, image_a: UUID, image_b: UUID) -> CandidatePair:
    """Resolve the open CandidatePair for two image uuids, mapping errors to HTTP."""
    ids = resolve_sorted_image_pair(db, image_a, image_b)
    if ids is None:
        raise HTTPException(status_code=404, detail="Image not found")
    candidate = db.execute(
        select(CandidatePair).where(
            CandidatePair.image1_id == ids[0],
            CandidatePair.image2_id == ids[1],
        )
    ).scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate pair not found")
    if candidate.status_id != CANDIDATE_OPEN:
        raise HTTPException(status_code=409, detail="Candidate not open")
    return candidate


def _build_annotation(payload: CandidateAnnotationCreateRequest, user: User, candidate: CandidatePair) -> CandidateAnnotation:
    return CandidateAnnotation(
        uuid=payload.uuid.bytes,
        created_at=now_ms(),
        created_by=user.id,
        candidate_id=candidate.id,
        no_overlap=bool(payload.no_overlap),
        expert_level=user.expert_level,
        status_id=STATUS_REVIEW_PENDING,
    )


@router.post("/create", response_model=CandidateAnnotationResponse, status_code=201)
def create_annotation(
    payload: CandidateAnnotationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_current_user(request)
    candidate = _resolve_open_candidate(db, payload.image_a, payload.image_b)
    annotation = _build_annotation(payload, user, candidate)
    db.add(annotation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Annotation already exists")
    db.refresh(annotation)
    return _to_response(annotation, db)


@router.post("/batch/create")
def batch_create_annotations(
    items: list[CandidateAnnotationCreateRequest],
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_current_user(request)

    annotations: list[CandidateAnnotation] = []
    for item in items:
        candidate = _resolve_open_candidate(db, item.image_a, item.image_b)
        annotation = _build_annotation(item, user, candidate)
        db.add(annotation)
        annotations.append(annotation)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Annotation already exists")

    db.commit()
    return {"created": len(annotations)}


@router.post("/correction", response_model=CandidateAnnotationResponse)
def correct_annotation(
    payload: CandidateAnnotationCorrectionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_current_user(request)

    annotation = db.execute(
        select(CandidateAnnotation).where(CandidateAnnotation.uuid == payload.uuid.bytes)
    ).scalar_one_or_none()
    if annotation is None:
        raise HTTPException(status_code=404, detail="Annotation not found")

    if annotation.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not the annotation creator")
    if annotation.status_id != STATUS_REVIEW_PENDING:
        raise HTTPException(status_code=409, detail="Annotation is not pending review")
    if now_ms() - annotation.created_at >= config.SELF_CORRECTION_TIME_LIMIT_MS:
        raise HTTPException(status_code=403, detail="Correction window expired")

    annotation.no_overlap = bool(payload.no_overlap)
    db.commit()
    db.refresh(annotation)
    return _to_response(annotation, db)


def _load_pending_for_review(db: Session, annotation_uuid: UUID) -> CandidateAnnotation:
    annotation = db.execute(
        select(CandidateAnnotation).where(CandidateAnnotation.uuid == annotation_uuid.bytes)
    ).scalar_one_or_none()
    if annotation is None:
        raise HTTPException(status_code=404, detail="Annotation not found")
    if annotation.status_id != STATUS_REVIEW_PENDING:
        raise HTTPException(status_code=409, detail="Annotation is not pending review")
    return annotation


def _authorize_review(caller: User, annotation: CandidateAnnotation) -> None:
    allowed = (caller.id != annotation.created_by) and (
        (caller.expert_level >= config.MIN_REVIEW_EXPERT_LEVEL and caller.expert_level > annotation.expert_level)
        or caller.role in (Role.SCIENTIST, Role.ADMIN)
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Not authorized to review this annotation")


def _apply_review(annotation: CandidateAnnotation, caller: User, status_id: int, db: Session) -> CandidateAnnotationResponse:
    annotation.status_id = status_id
    annotation.reviewed_by = caller.id
    annotation.reviewed_at = now_ms()
    db.commit()
    db.refresh(annotation)
    return _to_response(annotation, db)


@router.post("/review/{annotation_uuid}/fail", response_model=CandidateAnnotationResponse)
def review_fail(annotation_uuid: UUID, request: Request, db: Session = Depends(get_db)):
    caller = require_current_user(request)
    annotation = _load_pending_for_review(db, annotation_uuid)
    _authorize_review(caller, annotation)
    return _apply_review(annotation, caller, STATUS_REVIEW_FAILED, db)


@router.post("/review/{annotation_uuid}/approve", response_model=CandidateAnnotationResponse)
def review_approve(annotation_uuid: UUID, request: Request, db: Session = Depends(get_db)):
    caller = require_current_user(request)
    annotation = _load_pending_for_review(db, annotation_uuid)
    _authorize_review(caller, annotation)
    return _apply_review(annotation, caller, STATUS_APPROVED, db)


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


def _to_next_candidate_response(candidate: CandidatePair, db: Session) -> NextCandidateResponse:
    image1 = db.get(Image, candidate.image1_id)
    image2 = db.get(Image, candidate.image2_id)
    status_enum = INT_CANDIDATE_STATUS.get(candidate.status_id)
    return NextCandidateResponse(
        image1=_to_next_image_response(image1, db),
        image2=_to_next_image_response(image2, db),
        status=str(status_enum) if status_enum is not None else None,
    )


@router.get("/next/{dive_uuid}", response_model=list[NextCandidateResponse])
@router.get("/next/{dive_uuid}/{n}", response_model=list[NextCandidateResponse])
def get_next_candidates(dive_uuid: UUID, request: Request, n: int = 1, db: Session = Depends(get_db)):
    user = require_current_user(request)
    if n < 1:
        raise HTTPException(status_code=422, detail="n must be >= 1")

    dive = get_by_uuid(db, Dive, dive_uuid.bytes)
    if dive is None:
        raise HTTPException(status_code=404, detail="Dive not found")

    Image1 = aliased(Image)
    Image2 = aliased(Image)
    annotated_candidate_ids = select(CandidateAnnotation.candidate_id).where(
        CandidateAnnotation.created_by == user.id
    )

    stmt = (
        select(CandidatePair)
        .join(Image1, CandidatePair.image1_id == Image1.id)
        .join(Image2, CandidatePair.image2_id == Image2.id)
        .where(
            CandidatePair.status_id == CANDIDATE_OPEN,
            Image1.dive_id == dive.id,
            Image2.dive_id == dive.id,
            CandidatePair.id.notin_(annotated_candidate_ids),
        )
        .order_by(CandidatePair.created_at.asc())
        .limit(n)
    )
    candidates = db.execute(stmt).scalars().all()
    return [_to_next_candidate_response(candidate, db) for candidate in candidates]
