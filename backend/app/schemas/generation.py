from typing import Literal
from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    academic_year_id: int = 1
    solver_mode: Literal["cp_sat", "hybrid"] = "hybrid"
    time_limit_seconds: float = Field(10, gt=0, le=300)
    random_seed: int = 42


class GenerationResponse(BaseModel):
    run_id: int | None = None
    status: str
    objective_value: float | None
    runtime_seconds: float
    valid: bool
    assignments: list[dict]
    diagnostics: list[dict]
    metrics: dict
    refinement: dict | None = None

