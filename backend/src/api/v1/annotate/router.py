from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.v1.annotate.candidates import router as candidates_router
from src.api.v1.annotate.points import router as points_router
from src.api.v1.dataset._metadata import decode_metadata
from src.db import get_db
from src.models.annotate import LabelListResponse, LabelResponse
from src.models.dataset import DiveListResponse, DiveResponse, RegionListResponse, RegionResponse
from src.schema.cameras import Camera
from src.schema.dives import Dive
from src.schema.labels import Label
from src.schema.regions import Region
from src.schema.users import User
from src.services.lookups import get_by_uuid

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


@router.get("/dives", response_model=DiveListResponse)
def list_dives_for_region(region: UUID, db: Session = Depends(get_db)):
    """List dives within a region, so a player can pick one to fetch game candidates from.

    Unlike `/api/v1/dataset/dives` (scientist+, lists everything), this is
    open to any authenticated role and scoped to a single region, since
    that's all an annotator needs to start a game.
    """
    region_row = get_by_uuid(db, Region, region.bytes)
    if region_row is None:
        raise HTTPException(status_code=404, detail="Region not found")

    rows = db.execute(
        select(Dive, Camera, User)
        .join(Camera, Dive.camera_id == Camera.id)
        .join(User, Dive.created_by == User.id)
        .where(Dive.region_id == region_row.id)
        .order_by(Dive.created_at)
    ).all()
    return DiveListResponse(
        dives=[
            DiveResponse(
                uuid=UUID(bytes=dive.uuid),
                created_at=dive.created_at,
                created_by=UUID(bytes=creator.uuid),
                title=dive.title,
                metadata=decode_metadata(dive.metadata_json),
                description=dive.description,
                region=region,
                camera=UUID(bytes=camera.uuid),
            )
            for dive, camera, creator in rows
        ]
    )
