from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DatasetSummaryResponse(BaseModel):
    dive_count: int
    image_count: int
    image_pair_count: int


class LabelResponse(BaseModel):
    uuid: UUID
    created_at: int
    created_by: UUID
    scope: str
    title: str
    description: str | None


class RegionResponse(BaseModel):
    uuid: UUID
    created_at: int
    created_by: UUID
    title: str
    metadata: Any | None
    description: str | None


class CameraResponse(BaseModel):
    uuid: UUID
    created_at: int
    created_by: UUID
    title: str
    metadata: Any | None
    description: str | None


class DiveCreateRequest(BaseModel):
    uuid: UUID
    title: str = Field(min_length=1, max_length=127)
    metadata: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=1023)
    region: UUID
    camera: UUID


class DiveUpdateRequest(BaseModel):
    uuid: UUID
    title: str | None = Field(default=None, min_length=1, max_length=127)
    metadata: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=1023)
    region: UUID | None = None
    camera: UUID | None = None


class DiveResponse(BaseModel):
    uuid: UUID
    created_at: int
    created_by: UUID
    title: str
    metadata: Any | None
    description: str | None
    region: UUID
    camera: UUID


class DiveListResponse(BaseModel):
    dives: list[DiveResponse]


class ImageCreateRequest(BaseModel):
    uuid: UUID
    filename: str = Field(min_length=1, max_length=255)
    filepath: str = Field(min_length=1, max_length=1023)
    dive_uuid: UUID
    metadata: dict[str, Any] | None = None
    difficulty: int | None = None
    priority: int | None = None
    image: str


class ImageUpdateRequest(BaseModel):
    uuid: UUID
    filename: str | None = Field(default=None, min_length=1, max_length=255)
    filepath: str | None = Field(default=None, min_length=1, max_length=1023)
    dive_uuid: UUID | None = None
    metadata: dict[str, Any] | None = None
    difficulty: int | None = None
    priority: int | None = None
    image: str | None = None


class ImageResponse(BaseModel):
    uuid: UUID
    created_at: int
    created_by: UUID
    filename: str
    filepath: str
    dive: UUID
    status: str | None
    size_x: int
    size_y: int
    metadata: Any | None
    difficulty: int | None
    priority: int | None


class ImagePairRef(BaseModel):
    """A pair of images, referenced by their uuids."""

    image_a: UUID
    image_b: UUID


class CandidatePairResponse(BaseModel):
    created_at: int
    created_by: UUID
    image_a: UUID
    image_b: UUID
    status: str | None


class ImagePairResponse(BaseModel):
    created_at: int
    created_by: UUID
    image_a: UUID
    image_b: UUID
    difficulty: int | None
    priority: int | None
    status: str | None
