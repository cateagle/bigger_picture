from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.constants import Role


class UserSummary(BaseModel):
    uuid: UUID
    username: str
    role: Role
    expert_level: int


class UserListResponse(BaseModel):
    users: list[UserSummary]


class UserCreateRequest(BaseModel):
    """Request used to create a new user."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuid": "8f8b65dc-fbf2-4dfb-bff2-f34072bb97e2",
                "username": "jdoe",
                "role": "annotator",
                "expert_level": 0,
            }
        }
    )

    uuid: UUID = Field(description="Unique identifier to assign to the new user.")

    username: str = Field(
        min_length=1,
        max_length=64,
        description="Login name for the new user. Must be unique, case-insensitively.",
    )

    role: Role = Field(
        default=Role.ANNOTATOR, description="Permission level to grant the new user."
    )

    expert_level: int = Field(
        default=0, description="Initial annotation-weight for the new user."
    )


class UserUpdateRequest(BaseModel):
    """Request used to partially update an existing user.

    Only the fields explicitly supplied are changed; omitted fields are left
    untouched. Sending an explicit null for username, role, or expert_level is
    also a no-op, since none of these columns are nullable.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuid": "8f8b65dc-fbf2-4dfb-bff2-f34072bb97e2",
                "role": "scientist",
            }
        }
    )

    uuid: UUID = Field(description="Unique identifier of the user to update.")

    username: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="New login name. Must be unique, case-insensitively. Omit to leave unchanged.",
    )

    role: Role | None = Field(
        default=None, description="New permission level. Omit to leave unchanged."
    )

    expert_level: int | None = Field(
        default=None, description="New annotation-weight. Omit to leave unchanged."
    )
