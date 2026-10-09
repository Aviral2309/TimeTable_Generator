from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import GenerationRun
from app.schemas.generation import GenerationRequest, GenerationResponse
from app.services.generation import generate_demo

router = APIRouter(prefix="/api")


@router.get("/health")
def health(): return {"status": "ok"}


@router.post("/generation/demo", response_model=GenerationResponse)
def generate(request: GenerationRequest, db: Session = Depends(get_db)):
    try:
        return generate_demo(db, request.academic_year_id, request.solver_mode, request.time_limit_seconds, request.random_seed)
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, f"Generation failed: {exc}") from exc


@router.get("/generation/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.scalar(select(GenerationRun).where(GenerationRun.id == run_id))
    if not run: raise HTTPException(404, "Generation run not found")
    return {"id": run.id, "status": run.status, "solver_mode": run.solver_mode, "objective_value": run.objective_value, "runtime_seconds": run.runtime_seconds, "diagnostics": run.diagnostics}

