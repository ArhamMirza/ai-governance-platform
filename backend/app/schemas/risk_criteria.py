from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RiskCriteriaUpdate(BaseModel):
    medium_min_score: int
    high_min_score: int


class RiskCriteriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medium_min_score: int
    high_min_score: int
    # True when the bands match the built-in defaults, so the UI can badge them
    # as such. Independent of whether criteria were ever explicitly saved --
    # updated_at carries that (None = never saved).
    is_default: bool
    min_score: int
    max_score: int
    updated_at: datetime | None
