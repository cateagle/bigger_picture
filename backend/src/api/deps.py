from fastapi import HTTPException, Request

from src.schema.users import User


def get_current_user(request: Request) -> User | None:
    """Return the authenticated user resolved by AuthMiddleware, or None."""
    return request.state.user


def require_current_user(request: Request) -> User:
    """Return the authenticated user, raising 401 if there is none.

    On role-gated prefixes the middleware already guarantees a non-None user,
    so this is a safety net for handlers that read `created_by` etc.
    """
    user = request.state.user
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
