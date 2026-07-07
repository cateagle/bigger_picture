from pydantic import BaseModel

from src.constants import Role


class UserSummary(BaseModel):
    id: int
    username: str
    role: Role
    expert_level: int


class UserListResponse(BaseModel):
    users: list[UserSummary]
