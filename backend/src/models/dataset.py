from pydantic import BaseModel


class DatasetSummaryResponse(BaseModel):
    dive_count: int
    image_count: int
    image_pair_count: int
