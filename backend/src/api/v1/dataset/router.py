from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.v1.dataset.cameras import router as cameras_router
from src.api.v1.dataset.candidate_pairs import router as candidate_pairs_router
from src.api.v1.dataset.dives import router as dives_router
from src.api.v1.dataset.image_pairs import router as image_pairs_router
from src.api.v1.dataset.images import router as images_router
from src.api.v1.dataset.labels import router as labels_router
from src.api.v1.dataset.regions import router as regions_router
from src.db import get_db
from src.models.dataset import DatasetSummaryResponse
from src.schema.dives import Dive
from src.schema.image_pairs import ImagePair
from src.schema.images import Image

router = APIRouter()

router.include_router(labels_router, prefix="/labels")
router.include_router(regions_router, prefix="/regions")
router.include_router(cameras_router, prefix="/cameras")
router.include_router(dives_router, prefix="/dives")
router.include_router(images_router, prefix="/images")
router.include_router(candidate_pairs_router, prefix="/candidates")
router.include_router(image_pairs_router, prefix="/pairs")


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
    image_pair_count = db.execute(select(func.count()).select_from(ImagePair)).scalar_one()
    return DatasetSummaryResponse(
        dive_count=dive_count, image_count=image_count, image_pair_count=image_pair_count
    )
