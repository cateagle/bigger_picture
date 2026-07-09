from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.v1.dataset.cameras import router as cameras_router
from src.api.v1.dataset.candidate_pairs import router as candidate_pairs_router
from src.api.v1.dataset.dives import router as dives_router
from src.api.v1.dataset.fun_facts import router as fun_facts_router
from src.api.v1.dataset.image_pairs import router as image_pairs_router
from src.api.v1.dataset.images import router as images_router
from src.api.v1.dataset.labels import router as labels_router
from src.api.v1.dataset.point_annotations import router as point_annotations_router
from src.api.v1.dataset.regions import router as regions_router
from src.api.v1.dataset.zip_upload import router as zip_upload_router
from src.db import get_db
from src.models.dataset import (
    DatasetSummaryResponse,
    StatusEnumListResponse,
    StatusEnumResponse,
)
from src.schema.annotation_statuses import AnnotationStatusRow
from src.schema.candidate_statuses import CandidateStatusRow
from src.schema.dives import Dive
from src.schema.image_pairs import ImagePair
from src.schema.image_statuses import ImageStatusRow
from src.schema.images import Image
from src.schema.pair_statuses import PairStatusRow

router = APIRouter()

router.include_router(labels_router, prefix="/labels")
router.include_router(regions_router, prefix="/regions")
router.include_router(cameras_router, prefix="/cameras")
router.include_router(dives_router, prefix="/dives")
router.include_router(images_router, prefix="/images")
router.include_router(candidate_pairs_router, prefix="/candidates")
router.include_router(image_pairs_router, prefix="/pairs")
router.include_router(point_annotations_router, prefix="/annotations")
router.include_router(fun_facts_router, prefix="/fun-facts")
router.include_router(zip_upload_router)


@router.get(
    "/summary",
    response_model=DatasetSummaryResponse,
    summary="Get Dataset Summary",
    description="""
Return aggregate counts of dives, images, and image pairs. Requires the scientist role.
""",
)
def dataset_summary(db: Session = Depends(get_db)):
    dive_count = db.execute(select(func.count()).select_from(Dive)).scalar_one()
    image_count = db.execute(select(func.count()).select_from(Image)).scalar_one()
    image_pair_count = db.execute(
        select(func.count()).select_from(ImagePair)
    ).scalar_one()
    return DatasetSummaryResponse(
        dive_count=dive_count,
        image_count=image_count,
        image_pair_count=image_pair_count,
    )


@router.get(
    "/statuses",
    response_model=StatusEnumListResponse,
    summary="List Status Enums",
    description="""
Return every recognized status value, with its name and description, grouped by the entity type it applies to (images, image pairs, candidate pairs, and annotations).
""",
)
def list_status_enums(db: Session = Depends(get_db)):
    def _statuses(model) -> list[StatusEnumResponse]:
        rows = db.execute(select(model).order_by(model.id)).scalars().all()
        return [
            StatusEnumResponse(name=row.title, description=row.description)
            for row in rows
        ]

    return StatusEnumListResponse(
        image_statuses=_statuses(ImageStatusRow),
        pair_statuses=_statuses(PairStatusRow),
        candidate_statuses=_statuses(CandidateStatusRow),
        annotation_statuses=_statuses(AnnotationStatusRow),
    )
