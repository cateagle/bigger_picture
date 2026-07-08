from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import require_current_user
from src.constants import Role
from src.db import get_db
from src.models.admin import UserCreateRequest, UserUpdateRequest
from src.models.auth import UserResponse
from src.schema.users import User
from src.util import apply_partial_update, now_ms

router = APIRouter()


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        uuid=UUID(bytes=user.uuid),
        username=user.username,
        role=Role(user.role),
        expert_level=user.expert_level,
        created_at=user.created_at,
    )


@router.post(
    "/create",
    response_model=UserResponse,
    status_code=201,
    summary="Create User",
    description="""
Create a new user with the given uuid, username, role, and expert_level. Requires the admin role.

Fails with 409 if the uuid or username (case-insensitively) is already taken.
""",
)
def create_user(payload: UserCreateRequest, request: Request, db: Session = Depends(get_db)):
    admin = require_current_user(request)

    user = User(
        uuid=payload.uuid.bytes,
        created_at=now_ms(),
        created_by=admin.id,
        username=payload.username,
        role=str(payload.role),
        expert_level=payload.expert_level,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username or uuid already taken")
    db.refresh(user)
    return _to_response(user)


@router.post(
    "/update",
    response_model=UserResponse,
    summary="Update User",
    description="""
Partially update an existing user, identified by uuid. Requires the admin role.

Only the fields supplied in the request are changed; omitted fields are left as-is. Sending an explicit null for username, role, or expert_level is also a no-op.

Fails with 404 if the uuid is not found, or 409 if the new username is already taken (case-insensitively).
""",
)
def update_user(payload: UserUpdateRequest, request: Request, db: Session = Depends(get_db)):
    require_current_user(request)

    user = db.execute(select(User).where(User.uuid == payload.uuid.bytes)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    updates = apply_partial_update(
        payload,
        nullable_columns=set(),
        field_map={"username": "username", "role": "role", "expert_level": "expert_level"},
    )
    if "role" in updates:
        updates["role"] = str(updates["role"])
    for column, value in updates.items():
        setattr(user, column, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already taken")
    db.refresh(user)
    return _to_response(user)
