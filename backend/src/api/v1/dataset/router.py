from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.dataset import DatasetSummaryResponse
from src.schema.dives import Dive
from src.schema.image_pairs import ImagePair
from src.schema.images import Image

router = APIRouter()


@router.get("/summary", response_model=DatasetSummaryResponse)
def dataset_summary(db: Session = Depends(get_db)):
    dive_count = db.execute(select(func.count()).select_from(Dive)).scalar_one()
    image_count = db.execute(select(func.count()).select_from(Image)).scalar_one()
    image_pair_count = db.execute(select(func.count()).select_from(ImagePair)).scalar_one()
    return DatasetSummaryResponse(
        dive_count=dive_count, image_count=image_count, image_pair_count=image_pair_count
    )
