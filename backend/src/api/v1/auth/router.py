import sqlite3
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from src import config
from src.api.deps import get_current_user
from src.constants import Role
from src.db import get_db
from src.models.auth import LoginRequest, SignupRequest, UserResponse
from src.schema.users import User, create_self_referencing_user, lookup_user_by_username

router = APIRouter()

__all__ = ["router", "get_current_user"]


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        uuid=UUID(bytes=user.uuid),
        username=user.username,
        role=Role(user.role),
        expert_level=user.expert_level,
        created_at=user.created_at,
    )


def _set_session_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        config.COOKIE_NAME,
        config.encode_uuid(user.uuid),
        httponly=True,
        samesite="lax",
        secure=config.COOKIE_SECURE,
        path="/",
        max_age=config.COOKIE_MAX_AGE_SECONDS,
    )


@router.post("/signup", response_model=UserResponse, status_code=201)
def signup(payload: SignupRequest, request: Request, response: Response):
    engine = request.app.state.engine
    try:
        user = create_self_referencing_user(engine, username=payload.username, role=Role.ANNOTATOR)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already taken")

    _set_session_cookie(response, user)
    return _to_response(user)


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = lookup_user_by_username(db, payload.username)
    if user is None:
        raise HTTPException(status_code=404, detail="Unknown username")

    _set_session_cookie(response, user)
    return _to_response(user)


@router.get("/me", response_model=UserResponse)
def me(user: User | None = Depends(get_current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _to_response(user)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(config.COOKIE_NAME, path="/")
