from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
import csv
import io
from app.core.security import require_roles
from app.db.session import get_db
from app.models.entities import AcademicYear, CourseOffering, Department, Faculty, GenerationRun, Institute, Room, SemesterOffering, TimeSlot, Timetable, TimetableBackup, TimetableSession, User, ValidationReport
from app.schemas.generation import GenerationRequest, GenerationResponse, TimetableStatusRequest
from app.services.generation import generate_problem

router = APIRouter(prefix="/api")


@router.get("/health")
def health(): return {"status": "ok"}


@router.post("/generation", response_model=GenerationResponse)
def generate(request: GenerationRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if not request.semester_offering_ids:
        raise HTTPException(422, "Select configured semester cohorts; demo fallback is disabled")
    try:
        return generate_problem(db, request.academic_year_id, request.solver_mode, request.time_limit_seconds, request.random_seed, request.semester_offering_ids)
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, f"Generation failed: {exc}") from exc


@router.get("/generation/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    run = db.scalar(select(GenerationRun).where(GenerationRun.id == run_id))
    if not run: raise HTTPException(404, "Generation run not found")
    return {"id": run.id, "status": run.status, "solver_mode": run.solver_mode, "objective_value": run.objective_value, "runtime_seconds": run.runtime_seconds, "diagnostics": run.diagnostics}


def _timetable_payload(table: Timetable, db: Session, user: User):
    query = select(TimetableSession).where(TimetableSession.timetable_id == table.id)
    sessions = db.scalars(query).all()
    if user.role == "faculty" and user.faculty_id:
        sessions = [s for s in sessions if user.faculty_id in s.faculty_ids]
    if user.role == "student" and user.student_group_id:
        parts = user.student_group_id.split("-")
        cohort = "-".join(parts[:2]) if len(parts) >= 2 else user.student_group_id
        sessions = [s for s in sessions if any(group == user.student_group_id or group == cohort or (group.startswith(f"{cohort}-ELECTIVE") and "ELECTIVE" in group) for group in s.participant_group_ids)]
    offering_ids = {s.course_offering_id for s in sessions}
    offerings = {o.id: o for o in db.scalars(select(CourseOffering).where(CourseOffering.id.in_(offering_ids))).all()} if offering_ids else {}
    room_ids = {s.room_id for s in sessions}; rooms = {r.id: r for r in db.scalars(select(Room).where(Room.id.in_(room_ids))).all()} if room_ids else {}
    faculty_ids = {f for s in sessions for f in s.faculty_ids}; faculty = {f.id: f for f in db.scalars(select(Faculty).where(Faculty.id.in_(faculty_ids))).all()} if faculty_ids else {}
    semester_ids = {o.semester_offering_id for o in offerings.values()}; semesters = {s.id: s for s in db.scalars(select(SemesterOffering).where(SemesterOffering.id.in_(semester_ids))).all()} if semester_ids else {}
    enriched = []
    for s in sessions:
        o = offerings.get(s.course_offering_id); semester = semesters.get(o.semester_offering_id) if o else None
        enriched.append({"id": s.id, "course_offering_id": s.course_offering_id, "course_code": o.code if o else f"Course {s.course_offering_id}", "course_name": o.name if o else "Scheduled course", "kind": o.kind if o else ("lab" if s.duration_periods > 1 else "theory"), "session_type": s.session_type, "semester_number": semester.semester_number if semester else None, "day": s.day, "start_period": s.start_period, "duration_periods": s.duration_periods, "room_id": s.room_id, "room_code": rooms[s.room_id].code if s.room_id in rooms else str(s.room_id), "room_name": rooms[s.room_id].name if s.room_id in rooms else "", "faculty_ids": s.faculty_ids, "faculty_names": [faculty[x].name for x in s.faculty_ids if x in faculty], "faculty_codes": [faculty[x].faculty_code for x in s.faculty_ids if x in faculty], "participant_group_ids": s.participant_group_ids})
    institute = db.scalar(select(Institute).order_by(Institute.id).limit(1))
    year = db.get(AcademicYear, table.academic_year_id)
    department_ids = {semester.department_id for semester in semesters.values()}
    departments = {d.id: d for d in db.scalars(select(Department).where(Department.id.in_(department_ids))).all()} if department_ids else {}
    time_slots = db.scalars(select(TimeSlot).order_by(TimeSlot.period_index, TimeSlot.day)).all()
    subject_rows = [{"id": o.id, "semester_number": semesters[o.semester_offering_id].semester_number if o.semester_offering_id in semesters else None, "code": o.code, "name": o.name, "kind": o.kind, "sessions_per_week": o.sessions_per_week, "theory_sessions_per_week": o.theory_sessions_per_week, "lecture_sessions_per_week": o.lecture_sessions_per_week, "duration_periods": o.duration_periods, "elective_group": o.elective_group, "parallel_elective": o.parallel_elective, "faculty_names": [faculty[x].name for x in o.faculty_ids if x in faculty]} for o in offerings.values()]
    semester_rows = [{"id": semester.id, "semester_number": semester.semester_number, "strength": semester.strength, "department_name": departments[semester.department_id].name if semester.department_id in departments else "", "department_code": departments[semester.department_id].code if semester.department_id in departments else "", "home_room_code": (db.get(Room, semester.home_room_id).code if semester.home_room_id and db.get(Room, semester.home_room_id) else "")} for semester in semesters.values()]
    run = db.get(GenerationRun, table.generation_run_id)
    return {"id": table.id, "version": table.version, "status": table.status, "created_at": run.created_at if run else None, "institute_name": institute.name if institute else "", "academic_year_id": table.academic_year_id, "academic_year": year.name if year else "", "academic_term": year.term_type if year else "", "semesters": semester_rows, "subjects": subject_rows, "time_slots": [{"day": slot.day, "period_index": slot.period_index, "start_time": slot.start_time, "end_time": slot.end_time, "blocked": slot.blocked} for slot in time_slots], "sessions": enriched}


@router.get("/timetables/latest")
def latest_timetable(db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "faculty", "student"))):
    active_year = db.scalar(select(AcademicYear).where(AcademicYear.active.is_(True)).order_by(desc(AcademicYear.id)).limit(1))
    query = select(Timetable)
    target_year_id = user.academic_year_id if user.role == "student" and user.academic_year_id else (active_year.id if active_year else None)
    if target_year_id: query = query.where(Timetable.academic_year_id == target_year_id)
    if user.role != "admin": query = query.where(Timetable.status == "published")
    table = db.scalar(query.order_by(desc(Timetable.version), desc(Timetable.id)).limit(1))
    if not table: raise HTTPException(404, "No generated timetable exists for the active academic term")
    return _timetable_payload(table, db, user)


@router.get("/timetables")
def timetable_history(academic_year_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "faculty", "student"))):
    query = select(Timetable)
    if user.role == "student" and user.academic_year_id:
        academic_year_id = user.academic_year_id
    if academic_year_id: query = query.where(Timetable.academic_year_id == academic_year_id)
    if user.role != "admin": query = query.where(Timetable.status == "published")
    tables = db.scalars(query.order_by(desc(Timetable.id))).all()
    year_ids = {table.academic_year_id for table in tables}
    years = {year.id: year for year in db.scalars(select(AcademicYear).where(AcademicYear.id.in_(year_ids))).all()} if year_ids else {}
    run_ids = {table.generation_run_id for table in tables}
    runs = {run.id: run for run in db.scalars(select(GenerationRun).where(GenerationRun.id.in_(run_ids))).all()} if run_ids else {}
    return {"items": [{"id": table.id, "version": table.version, "status": table.status, "academic_year_id": table.academic_year_id, "academic_year": years[table.academic_year_id].name if table.academic_year_id in years else "", "academic_term": years[table.academic_year_id].term_type if table.academic_year_id in years else "", "created_at": runs[table.generation_run_id].created_at if table.generation_run_id in runs else None, "solver_mode": runs[table.generation_run_id].solver_mode if table.generation_run_id in runs else ""} for table in tables]}


@router.get("/timetables/{timetable_id}")
def timetable_by_id(timetable_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "faculty", "student"))):
    table = db.get(Timetable, timetable_id)
    if not table: raise HTTPException(404, "Timetable version not found")
    if user.role != "admin" and table.status != "published":
        raise HTTPException(403, "This timetable version has not been published")
    if user.role == "student" and user.academic_year_id and table.academic_year_id != user.academic_year_id:
        raise HTTPException(403, "This timetable is outside your selected academic year")
    return _timetable_payload(table, db, user)


@router.get("/timetables/{timetable_id}/validation")
def timetable_validation(timetable_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "faculty", "student"))):
    table = db.get(Timetable, timetable_id)
    if not table: raise HTTPException(404, "Timetable version not found")
    if user.role != "admin" and table.status != "published":
        raise HTTPException(403, "This timetable version has not been published")
    if user.role == "student" and user.academic_year_id and table.academic_year_id != user.academic_year_id:
        raise HTTPException(403, "This timetable is outside your selected academic year")
    run = db.get(GenerationRun, table.generation_run_id)
    report = db.scalar(select(ValidationReport).where(ValidationReport.generation_run_id == table.generation_run_id).order_by(desc(ValidationReport.id)).limit(1))
    if not report: raise HTTPException(404, "Validation report is unavailable for this legacy timetable")
    expected = db.scalar(select(func.count()).select_from(TimetableSession).where(TimetableSession.timetable_id == table.id)) or 0
    return {
        "timetable_id": table.id,
        "version": table.version,
        "valid": report.valid,
        "status": run.status if run else "unknown",
        "errors": report.errors,
        "diagnostics": run.diagnostics if run else [],
        "metrics": report.metrics,
        "scheduled_sessions": expected,
        "checked_at": run.created_at if run else None,
    }


@router.patch("/timetables/{timetable_id}/status")
def timetable_status(timetable_id: int, body: TimetableStatusRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    table = db.get(Timetable, timetable_id)
    if not table: raise HTTPException(404, "Timetable version not found")
    table.status = body.status
    db.commit(); db.refresh(table)
    return {"id": table.id, "version": table.version, "status": table.status}


@router.get("/timetable-backups")
def timetable_backups(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    items = db.scalars(select(TimetableBackup).order_by(desc(TimetableBackup.id))).all()
    return {"items": [{"id": item.id, "timetable_id": item.timetable_id, "academic_year_id": item.academic_year_id, "version": item.version, "reason": item.reason, "checksum": item.checksum, "created_at": item.created_at} for item in items]}


@router.get("/timetable-backups/{backup_id}")
def timetable_backup(backup_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(TimetableBackup, backup_id)
    if not item: raise HTTPException(404, "Timetable backup not found")
    return {"id": item.id, "created_at": item.created_at, "reason": item.reason, "checksum": item.checksum, "snapshot": item.snapshot}


@router.get("/export/latest.csv")
def export_latest(db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "faculty", "student"))):
    data = latest_timetable(db, user)
    stream = io.StringIO(); writer = csv.writer(stream)
    writer.writerow(["day", "start_period", "duration", "course_offering_id", "room_id", "faculty_ids", "participant_groups"])
    for s in data["sessions"]:
        value = s if isinstance(s, dict) else s.__dict__
        writer.writerow([value["day"], value["start_period"], value["duration_periods"], value["course_offering_id"], value["room_id"], ";".join(map(str, value["faculty_ids"])), ";".join(value["participant_group_ids"])])
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=timetable.csv"})


@router.get("/analytics/summary")
def analytics(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    runs = db.scalars(select(GenerationRun).order_by(desc(GenerationRun.id)).limit(10)).all()
    return {"recent_runs": [{"id": r.id, "status": r.status, "mode": r.solver_mode, "runtime": r.runtime_seconds, "objective": r.objective_value} for r in runs], "successful_runs": sum(r.status in {"optimal", "feasible"} for r in runs)}

