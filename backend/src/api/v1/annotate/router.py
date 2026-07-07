from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.annotate import LabelListResponse, LabelResponse
from src.schema.labels import Label

router = APIRouter()


@router.get("/labels", response_model=LabelListResponse)
def list_labels(db: Session = Depends(get_db)):
    labels = db.execute(select(Label)).scalars().all()
    return LabelListResponse(
        labels=[
            LabelResponse(id=label.id, scope=label.scope, title=label.title, description=label.description)
            for label in labels
        ]
    )
