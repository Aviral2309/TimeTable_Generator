from dataclasses import asdict
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.entities import GenerationRun, Timetable, TimetableSession, ValidationReport
from app.scheduling.annealing import refine
from app.scheduling.database_problem import build_database_problem
from app.scheduling.solver import solve
from app.scheduling.validator import validate_schedule


def generate_problem(db: Session, academic_year_id: int, mode: str, time_limit: float, seed: int, semester_ids: list[int] | None = None) -> dict:
    if not semester_ids:
        raise ValueError("No semester cohorts were selected")
    problem = build_database_problem(db, academic_year_id, semester_ids)
    run = GenerationRun(academic_year_id=academic_year_id, status="running", solver_mode=mode, weights=problem.weights)
    db.add(run); db.commit(); db.refresh(run)
    result = solve(problem, time_limit, seed)
    assignments, refinement = result.assignments, None
    if result.status in {"optimal", "feasible"} and mode == "hybrid":
        assignments, refinement = refine(problem, assignments, 5000, seed)
    valid, errors, metrics = validate_schedule(problem, assignments) if assignments else (False, [], {})
    diagnostics = result.diagnostics + errors
    run.status, run.objective_value, run.runtime_seconds, run.diagnostics = result.status, result.objective, result.runtime_seconds, diagnostics
    if assignments and valid:
        next_version = (db.scalar(select(func.max(Timetable.version)).where(Timetable.academic_year_id == academic_year_id)) or 0) + 1
        table = Timetable(generation_run_id=run.id, academic_year_id=academic_year_id, version=next_version)
        db.add(table); db.flush()
        for a in assignments:
            db.add(TimetableSession(timetable_id=table.id, course_offering_id=a.offering_id, occurrence=a.occurrence, day=a.day, start_period=a.start_period, duration_periods=a.duration, room_id=a.room_id, faculty_ids=list(a.faculty_ids), participant_group_ids=list(a.group_ids)))
    db.add(ValidationReport(generation_run_id=run.id, valid=valid, errors=errors, metrics=metrics))
    db.commit()
    return {"run_id": run.id, "status": result.status, "objective_value": result.objective, "runtime_seconds": result.runtime_seconds, "valid": valid, "assignments": [asdict(a) for a in assignments], "diagnostics": diagnostics, "metrics": metrics, "refinement": refinement}

