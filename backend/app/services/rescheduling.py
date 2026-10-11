from __future__ import annotations

from dataclasses import replace
from time import perf_counter

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    CourseOffering,
    Faculty,
    GenerationRun,
    RescheduleEvent,
    Room,
    SemesterOffering,
    Timetable,
    TimetableSession,
    ValidationReport,
)
from app.schemas.rescheduling import RescheduleRequest
from app.scheduling.database_problem import build_database_problem
from app.scheduling.domain import Assignment, ResourceReservation
from app.scheduling.solver import solve
from app.scheduling.validator import validate_schedule


CHANGE_PENALTY = 1_000_000


class ReschedulingError(ValueError):
    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {"message": message}


def _source_timetable(db: Session, timetable_id: int | None) -> Timetable:
    if timetable_id:
        table = db.get(Timetable, timetable_id)
    else:
        table = db.scalar(select(Timetable).order_by(desc(Timetable.id)).limit(1))
    if not table:
        raise ReschedulingError("No generated timetable exists to reschedule")
    return table


def _current_assignments(db: Session, table: Timetable) -> tuple[list[Assignment], list[int]]:
    rows = db.scalars(select(TimetableSession).where(TimetableSession.timetable_id == table.id)).all()
    if not rows:
        raise ReschedulingError("The selected timetable has no sessions")
    offering_ids = {row.course_offering_id for row in rows}
    offerings = db.scalars(select(CourseOffering).where(CourseOffering.id.in_(offering_ids))).all()
    semester_ids = sorted({offering.semester_offering_id for offering in offerings})
    assignments = [
        Assignment(
            session_id=f"offering-{row.course_offering_id}-{row.occurrence + 1}",
            offering_id=row.course_offering_id,
            occurrence=row.occurrence,
            day=row.day,
            start_period=row.start_period,
            duration=row.duration_periods,
            room_id=row.room_id,
            faculty_ids=tuple(row.faculty_ids),
            group_ids=tuple(row.participant_group_ids),
        )
        for row in rows
    ]
    return assignments, semester_ids


def _event_reservation(db: Session, request: RescheduleRequest, problem) -> tuple[ResourceReservation, str]:
    if request.day not in problem.days:
        raise ReschedulingError(f"{request.day} is not part of the configured working week")
    periods = tuple(range(request.start_period, request.start_period + request.duration_periods))
    invalid = [period for period in periods if period not in problem.periods]
    if invalid:
        raise ReschedulingError("The unavailable interval extends outside configured timetable periods", {"invalid_periods": invalid})
    if request.resource_type == "faculty":
        resource = db.get(Faculty, request.resource_id)
        if not resource or request.resource_id not in problem.faculty:
            raise ReschedulingError("Faculty record is missing or inactive")
        return ResourceReservation(request.day, periods, faculty_id=request.resource_id, description=request.reason), f"{resource.faculty_code} · {resource.name}"
    resource = db.get(Room, request.resource_id)
    if not resource or request.resource_id not in problem.rooms:
        raise ReschedulingError("Room record is missing or inactive")
    return ResourceReservation(request.day, periods, room_id=request.resource_id, description=request.reason), f"{resource.code} · {resource.name}"


def _overlaps(assignment: Assignment, request: RescheduleRequest) -> bool:
    if assignment.day != request.day:
        return False
    event_periods = set(range(request.start_period, request.start_period + request.duration_periods))
    session_periods = set(range(assignment.start_period, assignment.start_period + assignment.duration))
    if not event_periods.intersection(session_periods):
        return False
    return assignment.room_id == request.resource_id if request.resource_type == "room" else request.resource_id in assignment.faculty_ids


def _change_rows(db: Session, problem, current: list[Assignment], proposed: list[Assignment]) -> list[dict]:
    before = {assignment.session_id: assignment for assignment in current}
    sessions = {session.id: session for session in problem.sessions}
    offering_ids = {assignment.offering_id for assignment in proposed}
    offerings = {item.id: item for item in db.scalars(select(CourseOffering).where(CourseOffering.id.in_(offering_ids))).all()}
    semester_ids = {item.semester_offering_id for item in offerings.values()}
    semesters = {item.id: item for item in db.scalars(select(SemesterOffering).where(SemesterOffering.id.in_(semester_ids))).all()}
    room_ids = {assignment.room_id for assignment in current + proposed}
    rooms = {item.id: item for item in db.scalars(select(Room).where(Room.id.in_(room_ids))).all()}
    changes = []
    for after in proposed:
        old = before.get(after.session_id)
        if not old or (old.day, old.start_period, old.room_id) == (after.day, after.start_period, after.room_id):
            continue
        offering = offerings[after.offering_id]
        semester = semesters[offering.semester_offering_id]
        session = sessions[after.session_id]
        changes.append({
            "session_id": after.session_id,
            "course_code": offering.code,
            "course_name": offering.name,
            "semester_number": semester.semester_number,
            "kind": offering.kind,
            "participant_group_ids": list(session.group_ids),
            "before": {"day": old.day, "start_period": old.start_period, "duration_periods": old.duration, "room_id": old.room_id, "room_code": rooms[old.room_id].code},
            "after": {"day": after.day, "start_period": after.start_period, "duration_periods": after.duration, "room_id": after.room_id, "room_code": rooms[after.room_id].code},
        })
    return sorted(changes, key=lambda item: (item["semester_number"], item["before"]["day"], item["before"]["start_period"], item["course_code"]))


def plan_reschedule(db: Session, request: RescheduleRequest) -> dict:
    started = perf_counter()
    table = _source_timetable(db, request.source_timetable_id)
    current, semester_ids = _current_assignments(db, table)
    problem = build_database_problem(db, table.academic_year_id, semester_ids)
    reservation, resource_name = _event_reservation(db, request, problem)
    disrupted_problem = replace(problem, reservations=[*problem.reservations, reservation])
    affected = [assignment.session_id for assignment in current if _overlaps(assignment, request)]
    if not affected:
        valid, errors, metrics = validate_schedule(disrupted_problem, current)
        return {
            "source_timetable_id": table.id,
            "source_version": table.version,
            "status": "no_change_needed",
            "valid": valid,
            "resource_name": resource_name,
            "affected_session_ids": [],
            "affected_sessions": 0,
            "moved_sessions": 0,
            "changes": [],
            "diagnostics": errors or [{"code": "no_affected_sessions", "message": "No scheduled class uses this resource during the selected interval."}],
            "metrics": metrics,
            "assignments": current,
            "runtime_seconds": perf_counter() - started,
            "problem": disrupted_problem,
            "solver_objective": 0,
        }
    result = solve(disrupted_problem, request.time_limit_seconds, request.random_seed, baseline=current, change_penalty=CHANGE_PENALTY)
    proposed = result.assignments
    valid, errors, metrics = validate_schedule(disrupted_problem, proposed) if proposed else (False, [], {})
    diagnostics = [*result.diagnostics, *errors]
    if not proposed:
        diagnostics.append({
            "code": "reschedule_infeasible",
            "message": "No valid alternative was found. Affected classes may be fixed, or every compatible faculty/room/time option may already be occupied.",
        })
    changes = _change_rows(db, disrupted_problem, current, proposed) if proposed else []
    return {
        "source_timetable_id": table.id,
        "source_version": table.version,
        "status": result.status,
        "valid": valid,
        "resource_name": resource_name,
        "affected_session_ids": affected,
        "affected_sessions": len(affected),
        "moved_sessions": len(changes),
        "changes": changes,
        "diagnostics": diagnostics,
        "metrics": metrics,
        "assignments": proposed,
        "runtime_seconds": perf_counter() - started,
        "problem": disrupted_problem,
        "solver_objective": result.objective,
    }


def public_plan(plan: dict) -> dict:
    return {key: value for key, value in plan.items() if key not in {"assignments", "problem", "solver_objective"}}


def apply_reschedule(db: Session, request: RescheduleRequest, user_id: int | None) -> dict:
    plan = plan_reschedule(db, request)
    if plan["status"] == "no_change_needed":
        raise ReschedulingError("No timetable session is affected, so no new version was created", public_plan(plan))
    if not plan["valid"] or not plan["assignments"]:
        raise ReschedulingError("The requested disruption cannot be resolved without violating constraints", public_plan(plan))
    source = db.get(Timetable, plan["source_timetable_id"])
    latest_id = db.scalar(select(Timetable.id).where(Timetable.academic_year_id == source.academic_year_id).order_by(desc(Timetable.version)).limit(1))
    if latest_id != source.id:
        raise ReschedulingError("A newer timetable version exists. Preview the disruption again using the latest version.")
    run = GenerationRun(
        academic_year_id=source.academic_year_id,
        status=plan["status"],
        solver_mode="dynamic_reschedule",
        weights={**plan["problem"].weights, "change_penalty": CHANGE_PENALTY},
        objective_value=plan["solver_objective"],
        runtime_seconds=plan["runtime_seconds"],
        diagnostics=plan["diagnostics"],
    )
    db.add(run)
    db.flush()
    next_version = (db.scalar(select(func.max(Timetable.version)).where(Timetable.academic_year_id == source.academic_year_id)) or 0) + 1
    table = Timetable(generation_run_id=run.id, academic_year_id=source.academic_year_id, version=next_version, status="draft")
    db.add(table)
    db.flush()
    for assignment in plan["assignments"]:
        db.add(TimetableSession(
            timetable_id=table.id,
            course_offering_id=assignment.offering_id,
            occurrence=assignment.occurrence,
            day=assignment.day,
            start_period=assignment.start_period,
            duration_periods=assignment.duration,
            room_id=assignment.room_id,
            faculty_ids=list(assignment.faculty_ids),
            participant_group_ids=list(assignment.group_ids),
        ))
    db.add(ValidationReport(generation_run_id=run.id, valid=True, errors=[], metrics=plan["metrics"]))
    event = RescheduleEvent(
        source_timetable_id=source.id,
        result_timetable_id=table.id,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        day=request.day,
        start_period=request.start_period,
        duration_periods=request.duration_periods,
        reason=request.reason,
        status="applied",
        affected_sessions=plan["affected_sessions"],
        moved_sessions=plan["moved_sessions"],
        diagnostics=plan["diagnostics"],
        created_by_user_id=user_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    response = public_plan(plan)
    response.update({"event_id": event.id, "result_timetable_id": table.id, "result_version": table.version})
    return response
