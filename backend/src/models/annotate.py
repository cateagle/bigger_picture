from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LabelResponse(BaseModel):
    uuid: UUID
    scope: str
    title: str
    description: str | None


class LabelListResponse(BaseModel):
    labels: list[LabelResponse]


class CandidateAnnotationCreateRequest(BaseModel):
    uuid: UUID
    image_a: UUID
    image_b: UUID
    no_overlap: bool


class CandidateAnnotationCorrectionRequest(BaseModel):
    uuid: UUID
    no_overlap: bool


class CandidateAnnotationResponse(BaseModel):
    uuid: UUID
    image_a: UUID
    image_b: UUID
    no_overlap: bool
    expert_level: int
    status: str
    created_at: int
    created_by: UUID
    reviewed_at: Optional[int]
    reviewed_by: Optional[UUID]


class PointAnnotationCreateRequest(BaseModel):
    uuid: UUID
    image_a: UUID
    image_b: UUID
    label_id: Optional[UUID] = None
    x1: int = Field(ge=0)
    y1: int = Field(ge=0)
    x2: int = Field(ge=0)
    y2: int = Field(ge=0)


class PointAnnotationCorrectionRequest(BaseModel):
    """Request used to correct an existing point annotation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuid": "8f8b65dc-fbf2-4dfb-bff2-f34072bb97e2",
                "label_id": "1a6ccf07-c766-4934-a6a5-0ca6dbdb5a0b",
                "x1": 125,
                "y1": 240,
                "x2": 89,
                "y2": 247,
            }
        }
    )

    uuid: UUID = Field(description="Unique identifier of the annotation to update.")

    label_id: Optional[UUID] = Field(
        default=None,
        description="Optional new label for the annotation. If omitted, the current label is kept.",
    )

    x1: int = Field(ge=0, description="X coordinate of image 1 in pixels.")

    y1: int = Field(ge=0, description="Y coordinate of image 1 in pixels.")

    x2: int = Field(ge=0, description="X coordinate of image 2 in pixels.")

    y2: int = Field(ge=0, description="Y coordinate of image 2 pixels.")


class PointAnnotationResponse(BaseModel):
    uuid: UUID
    image_a: UUID
    image_b: UUID
    label_id: Optional[UUID]
    x1: int
    y1: int
    x2: int
    y2: int
    expert_level: int
    confidence: Optional[float]
    status: str
    created_at: int
    created_by: UUID
    reviewed_at: Optional[int]
    reviewed_by: Optional[UUID]


class NextPairImageResponse(BaseModel):
    uuid: UUID
    filename: str
    filepath: str
    dive_id: UUID
    status: str | None
    size_x: int
    size_y: int
    metadata: Any | None


class NextPairResponse(BaseModel):
    image1: NextPairImageResponse
    image2: NextPairImageResponse
    difficulty: int | None
    priority: int | None
    status: str | None


class NextCandidateResponse(BaseModel):
    image1: NextPairImageResponse
    image2: NextPairImageResponse
    status: str | None
