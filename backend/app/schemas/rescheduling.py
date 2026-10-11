from typing import Literal

from pydantic import BaseModel, Field


class RescheduleRequest(BaseModel):
    source_timetable_id: int | None = None
    resource_type: Literal["faculty", "room"]
    resource_id: int = Field(gt=0)
    day: str = Field(min_length=2, max_length=12)
    start_period: int = Field(ge=0)
    duration_periods: int = Field(default=1, ge=1, le=12)
    reason: str = Field(min_length=3, max_length=300)
    time_limit_seconds: float = Field(default=20, gt=0, le=120)
    random_seed: int = 42
