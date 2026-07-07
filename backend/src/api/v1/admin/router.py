from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.admin import UserListResponse, UserSummary
from src.schema.users import User

router = APIRouter()


@router.get("/users", response_model=UserListResponse)
def list_users(db: Session = Depends(get_db)):
    users = db.execute(select(User)).scalars().all()
    return UserListResponse(
        users=[
            UserSummary(id=user.id, username=user.username, role=user.role, expert_level=user.expert_level)
            for user in users
        ]
    )
