from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.dataset import HelperImageListResponse, HelperImageResponse
from src.schema.helper_images import HelperImage
from src.schema.users import User

router = APIRouter()


def helper_image_to_response(helper_image: HelperImage, db: Session) -> HelperImageResponse:
    creator = db.get(User, helper_image.created_by)
    return HelperImageResponse(
        uuid=UUID(bytes=helper_image.uuid),
        created_at=helper_image.created_at,
        created_by=UUID(bytes=creator.uuid),
        filename=helper_image.filename,
        filepath=helper_image.filepath,
    )


@router.get(
    "",
    response_model=HelperImageListResponse,
    summary="List Helper Images",
    description="""
Return a page of every helper image in the system, ordered by creation time.

Helper images are decorative image assets (e.g. attached to fun facts); they are uploaded only via the endpoints that use them (currently fun facts create/update), not created directly here. Requires the scientist role.
""",
)
def list_helper_images(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    total = db.execute(select(func.count()).select_from(HelperImage)).scalar_one()
    helper_images = db.execute(
        select(HelperImage).order_by(HelperImage.created_at).limit(page_size).offset((page - 1) * page_size)
    ).scalars().all()
    return HelperImageListResponse(
        helper_images=[helper_image_to_response(h, db) for h in helper_images],
        total=total,
    )
