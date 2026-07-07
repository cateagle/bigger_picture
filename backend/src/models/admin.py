from uuid import UUID

from pydantic import BaseModel, Field

from src.constants import Role


class UserSummary(BaseModel):
    uuid: UUID
    username: str
    role: Role
    expert_level: int


class UserListResponse(BaseModel):
    users: list[UserSummary]


class UserCreateRequest(BaseModel):
    uuid: UUID
    username: str = Field(min_length=1, max_length=64)
    role: Role = Role.ANNOTATOR
    expert_level: int = 0


class UserUpdateRequest(BaseModel):
    uuid: UUID
    username: str | None = Field(default=None, min_length=1, max_length=64)
    role: Role | None = None
    expert_level: int | None = None
