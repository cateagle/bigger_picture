from pydantic import BaseModel


class LabelResponse(BaseModel):
    id: int
    scope: str
    title: str
    description: str | None


class LabelListResponse(BaseModel):
    labels: list[LabelResponse]
