from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.v1.annotate.candidates import router as candidates_router
from src.api.v1.annotate.points import router as points_router
from src.db import get_db
from src.models.annotate import LabelListResponse, LabelResponse
from src.schema.labels import Label

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
