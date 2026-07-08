from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.constants import Role


class SignupRequest(BaseModel):
    """Request used to create a new self-service account."""

    model_config = ConfigDict(json_schema_extra={"example": {"username": "jdoe"}})

    username: str = Field(
        min_length=1,
        max_length=64,
        description="Desired login name. Must be unique, case-insensitively. The new account is always created with the annotator role.",
    )


class LoginRequest(BaseModel):
    """Request used to start a session for an existing account."""

    model_config = ConfigDict(json_schema_extra={"example": {"username": "jdoe"}})

    username: str = Field(
        min_length=1,
        max_length=64,
        description="Login name of the existing account. Authentication is by username alone; there is no password.",
    )


class UserResponse(BaseModel):
    """User record returned by the auth and admin endpoints."""

    uuid: UUID = Field(description="Unique identifier of the user.")
    username: str = Field(description="Login name of the user.")
    role: Role = Field(
        description="Permission level of the user (annotator, scientist, or admin)."
    )
    expert_level: int = Field(
        description="Annotation-weight used to gate review permissions; unrelated to role. Read-only, derived from exp."
    )
    exp: int = Field(description="Total experience points the user has earned.")
    created_at: int = Field(
        description="Unix epoch time in milliseconds when the user was created."
    )


class StoryUpdateRequest(BaseModel):
    """Request used to overwrite the caller's own story progression."""

    model_config = ConfigDict(json_schema_extra={"example": {"story": {"chapter": 2}}})

    story: Any | None = Field(
        description="Arbitrary JSON object describing the caller's story progression. Send null to clear it."
    )


class StoryResponse(BaseModel):
    """The caller's own story progression."""

    story: Any | None = Field(description="Arbitrary caller-supplied JSON object, or null.")
