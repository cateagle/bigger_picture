from uuid import UUID

from pydantic import BaseModel, Field

from src.constants import Role


class SignupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)


class UserResponse(BaseModel):
    uuid: UUID
    username: str
    role: Role
    expert_level: int
    created_at: int
