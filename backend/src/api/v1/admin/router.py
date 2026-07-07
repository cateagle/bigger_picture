from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.v1.admin.users import router as users_router
from src.db import get_db
from src.models.admin import UserListResponse, UserSummary
from src.schema.users import User

router = APIRouter()

router.include_router(users_router, prefix="/users")


@router.get("/users", response_model=UserListResponse)
def list_users(db: Session = Depends(get_db)):
    users = db.execute(select(User)).scalars().all()
    return UserListResponse(
        users=[
            UserSummary(
                uuid=UUID(bytes=user.uuid),
                username=user.username,
                role=user.role,
                expert_level=user.expert_level,
            )
            for user in users
        ]
    )
