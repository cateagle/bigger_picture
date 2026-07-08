import sqlite3
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from src import config
from src.api.deps import get_current_user, require_current_user
from src.api.v1.dataset._metadata import decode_metadata, encode_metadata
from src.constants import Role
from src.db import get_db
from src.models.auth import (
    LoginRequest,
    SignupRequest,
    StoryResponse,
    StoryUpdateRequest,
    UserResponse,
)
from src.schema.users import User, create_self_referencing_user, lookup_user_by_username

router = APIRouter()

__all__ = ["router", "get_current_user"]


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        uuid=UUID(bytes=user.uuid),
        username=user.username,
        role=Role(user.role),
        expert_level=user.expert_level,
        exp=user.exp,
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


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=201,
    summary="Sign Up",
    description="""
Create a new self-service account with the given username and start a session for it. Always creates the account with the annotator role; role cannot be chosen or elevated at signup.

Sets a session cookie on success. Fails with 409 if the username is already taken (case-insensitively).
""",
)
def signup(payload: SignupRequest, request: Request, response: Response):
    engine = request.app.state.engine
    try:
        user = create_self_referencing_user(engine, username=payload.username, role=Role.ANNOTATOR)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already taken")

    _set_session_cookie(response, user)
    return _to_response(user)


@router.post(
    "/login",
    response_model=UserResponse,
    summary="Log In",
    description="""
Start a session for an existing account, identified by username alone; there is no password.

Sets a session cookie on success. Fails with 404 if the username is not registered.
""",
)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = lookup_user_by_username(db, payload.username)
    if user is None:
        raise HTTPException(status_code=404, detail="Unknown username")

    _set_session_cookie(response, user)
    return _to_response(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="""
Return the user for the current session cookie.

Fails with 401 if there is no valid session.
""",
)
def me(user: User | None = Depends(get_current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _to_response(user)


@router.post(
    "/logout",
    status_code=204,
    summary="Log Out",
    description="""
Clear the session cookie. Always succeeds, even if no session was active.
""",
)
def logout(response: Response):
    response.delete_cookie(config.COOKIE_NAME, path="/")


@router.get(
    "/story",
    response_model=StoryResponse,
    summary="Get Story",
    description="""
Return the caller's own story progression.

Fails with 401 if there is no valid session.
""",
)
def get_story(request: Request):
    user = require_current_user(request)
    return StoryResponse(story=decode_metadata(user.story))


@router.post(
    "/story",
    response_model=StoryResponse,
    summary="Update Story",
    description="""
Overwrite the caller's own story progression with an arbitrary JSON object. Sending null clears it.

Fails with 401 if there is no valid session.
""",
)
def update_story(payload: StoryUpdateRequest, request: Request, db: Session = Depends(get_db)):
    caller = require_current_user(request)
    user = db.get(User, caller.id)
    user.story = encode_metadata(payload.story)
    db.commit()
    db.refresh(user)
    return StoryResponse(story=decode_metadata(user.story))
