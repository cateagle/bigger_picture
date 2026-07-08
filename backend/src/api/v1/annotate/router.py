from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.v1.annotate.candidates import router as candidates_router
from src.api.v1.annotate.points import router as points_router
from src.api.v1.dataset._metadata import decode_metadata
from src.db import get_db
from src.models.annotate import LabelListResponse, LabelResponse
from src.models.dataset import RegionListResponse, RegionResponse
from src.schema.labels import Label
from src.schema.regions import Region
from src.schema.users import User

router = APIRouter()

router.include_router(candidates_router, prefix="/candidate")
router.include_router(points_router, prefix="/points")


@router.get("/labels", response_model=LabelListResponse)
def list_labels(db: Session = Depends(get_db)):
    labels = db.execute(select(Label)).scalars().all()
    return LabelListResponse(
        labels=[
            LabelResponse(
                uuid=UUID(bytes=label.uuid),
                scope=label.scope,
                title=label.title,
                description=label.description,
            )
            for label in labels
        ]
    )


@router.get("/regions", response_model=RegionListResponse)
def list_regions(db: Session = Depends(get_db)):
    regions = db.execute(select(Region)).scalars().all()
    return RegionListResponse(
        regions=[
            RegionResponse(
                uuid=UUID(bytes=region.uuid),
                created_at=region.created_at,
                created_by=UUID(bytes=db.get(User, region.created_by).uuid),
                title=region.title,
                metadata=decode_metadata(region.metadata_json),
                description=region.description,
            )
            for region in regions
        ]
    )
