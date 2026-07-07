import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from src import config
from src.constants import Role
from src.models.auth import SignupRequest, UserResponse
from src.schema.users import User, create_self_referencing_user

router = APIRouter()


def get_current_user(request: Request) -> User | None:
    return request.state.user


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        uuid=config.encode_uuid(user.uuid),
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


@router.get("/me", response_model=UserResponse)
def me(user: User | None = Depends(get_current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _to_response(user)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(config.COOKIE_NAME, path="/")
