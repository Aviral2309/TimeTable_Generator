from dataclasses import asdict
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.entities import GenerationRun, Timetable, TimetableSession, ValidationReport
from app.scheduling.annealing import refine, soft_cost
from app.scheduling.database_problem import build_database_problem
from app.scheduling.domain import Assignment, Problem
from app.scheduling.solver import solve
from app.scheduling.validator import validate_schedule
from app.services.backups import create_timetable_backup


def best_compatible_assignments(db: Session, problem: Problem, academic_year_id: int) -> list[Assignment] | None:
    """Find the strongest saved placement that still validates against current master data."""
    tables = db.scalars(
        select(Timetable)
        .where(Timetable.academic_year_id == academic_year_id)
        .order_by(Timetable.version.desc())
    ).all()
    required = {(session.offering_id, session.occurrence): session for session in problem.sessions}
    best: list[Assignment] | None = None
    best_cost: float | None = None
    for table in tables:
        rows = db.scalars(select(TimetableSession).where(TimetableSession.timetable_id == table.id)).all()
        if len(rows) != len(required):
            continue
        assignments: list[Assignment] = []
        for row in rows:
            session = required.get((row.course_offering_id, row.occurrence))
            if not session:
                assignments = []
                break
            assignments.append(Assignment(
                session.id,
                session.offering_id,
                session.occurrence,
                row.day,
                row.start_period,
                session.duration,
                row.room_id,
                session.faculty_ids,
                session.group_ids,
                session.session_type,
            ))
        valid, _, _ = validate_schedule(problem, assignments)
        if valid:
            cost = soft_cost(problem, assignments)
            if best_cost is None or cost < best_cost:
                best, best_cost = assignments, cost
    return best


def generate_problem(db: Session, academic_year_id: int, mode: str, time_limit: float, seed: int, semester_ids: list[int] | None = None) -> dict:
    if not semester_ids:
        raise ValueError("No semester cohorts were selected")
    problem = build_database_problem(db, academic_year_id, semester_ids)
    run = GenerationRun(academic_year_id=academic_year_id, status="running", solver_mode=mode, weights=problem.weights)
    db.add(run); db.commit(); db.refresh(run)
    result = solve(problem, time_limit, seed)
    assignments, refinement = result.assignments, None
    if result.status in {"optimal", "feasible"} and mode == "hybrid":
        # Multiple deterministic starts are more reliable than accepting one
        # random local optimum. A compatible prior timetable is one of the
        # starts, which guarantees generation cannot regress from a good layout.
        previous = best_compatible_assignments(db, problem, academic_year_id)
        starts = [assignments, assignments, previous or assignments]
        candidates = [refine(problem, start, 7000, seed + offset) for offset, start in enumerate(starts)]
        assignments, best_details = min(candidates, key=lambda item: soft_cost(problem, item[0]))
        refinement = {
            **best_details,
            "strategy": "best_of_three",
            "used_previous_timetable": previous is not None,
            "candidate_costs": [soft_cost(problem, candidate) for candidate, _ in candidates],
        }
    valid, errors, metrics = validate_schedule(problem, assignments) if assignments else (False, [], {})
    diagnostics = result.diagnostics + errors
    run.status, run.objective_value, run.runtime_seconds, run.diagnostics = result.status, result.objective, result.runtime_seconds, diagnostics
    if assignments and valid:
        next_version = (db.scalar(select(func.max(Timetable.version)).where(Timetable.academic_year_id == academic_year_id)) or 0) + 1
        table = Timetable(generation_run_id=run.id, academic_year_id=academic_year_id, version=next_version)
        db.add(table); db.flush()
        for a in assignments:
            db.add(TimetableSession(timetable_id=table.id, course_offering_id=a.offering_id, occurrence=a.occurrence, day=a.day, start_period=a.start_period, duration_periods=a.duration, session_type=a.session_type, room_id=a.room_id, faculty_ids=list(a.faculty_ids), participant_group_ids=list(a.group_ids)))
        create_timetable_backup(db, table, assignments, metrics)
    db.add(ValidationReport(generation_run_id=run.id, valid=valid, errors=errors, metrics=metrics))
    db.commit()
    return {"run_id": run.id, "status": result.status, "objective_value": result.objective, "runtime_seconds": result.runtime_seconds, "valid": valid, "assignments": [asdict(a) for a in assignments], "diagnostics": diagnostics, "metrics": metrics, "refinement": refinement}

