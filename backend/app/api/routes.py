from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
import csv
import io
from app.core.security import require_roles
from app.db.session import get_db
from app.models.entities import CourseOffering, Faculty, GenerationRun, Room, SemesterOffering, Timetable, TimetableSession, User
from app.schemas.generation import GenerationRequest, GenerationResponse
from app.services.generation import generate_problem

router = APIRouter(prefix="/api")


@router.get("/health")
def health(): return {"status": "ok"}


@router.post("/generation/demo", response_model=GenerationResponse)
def generate(request: GenerationRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    try:
        return generate_problem(db, request.academic_year_id, request.solver_mode, request.time_limit_seconds, request.random_seed, request.semester_offering_ids)
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, f"Generation failed: {exc}") from exc


@router.get("/generation/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "faculty"))):
    run = db.scalar(select(GenerationRun).where(GenerationRun.id == run_id))
    if not run: raise HTTPException(404, "Generation run not found")
    return {"id": run.id, "status": run.status, "solver_mode": run.solver_mode, "objective_value": run.objective_value, "runtime_seconds": run.runtime_seconds, "diagnostics": run.diagnostics}


@router.get("/timetables/latest")
def latest_timetable(db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "faculty", "student"))):
    table = db.scalar(select(Timetable).order_by(desc(Timetable.id)).limit(1))
    if not table: raise HTTPException(404, "No generated timetable exists")
    query = select(TimetableSession).where(TimetableSession.timetable_id == table.id)
    sessions = db.scalars(query).all()
    if user.role == "faculty" and user.faculty_id:
        sessions = [s for s in sessions if user.faculty_id in s.faculty_ids]
    if user.role == "student" and user.student_group_id:
        sessions = [s for s in sessions if user.student_group_id in s.participant_group_ids]
    offering_ids = {s.course_offering_id for s in sessions}
    offerings = {o.id: o for o in db.scalars(select(CourseOffering).where(CourseOffering.id.in_(offering_ids))).all()} if offering_ids else {}
    room_ids = {s.room_id for s in sessions}; rooms = {r.id: r for r in db.scalars(select(Room).where(Room.id.in_(room_ids))).all()} if room_ids else {}
    faculty_ids = {f for s in sessions for f in s.faculty_ids}; faculty = {f.id: f for f in db.scalars(select(Faculty).where(Faculty.id.in_(faculty_ids))).all()} if faculty_ids else {}
    semester_ids = {o.semester_offering_id for o in offerings.values()}; semesters = {s.id: s for s in db.scalars(select(SemesterOffering).where(SemesterOffering.id.in_(semester_ids))).all()} if semester_ids else {}
    enriched = []
    for s in sessions:
        o = offerings.get(s.course_offering_id); semester = semesters.get(o.semester_offering_id) if o else None
        enriched.append({"id": s.id, "course_offering_id": s.course_offering_id, "course_code": o.code if o else f"Course {s.course_offering_id}", "course_name": o.name if o else "Scheduled course", "kind": o.kind if o else ("lab" if s.duration_periods > 1 else "theory"), "semester_number": semester.semester_number if semester else None, "day": s.day, "start_period": s.start_period, "duration_periods": s.duration_periods, "room_id": s.room_id, "room_code": rooms[s.room_id].code if s.room_id in rooms else str(s.room_id), "faculty_ids": s.faculty_ids, "faculty_names": [faculty[x].name for x in s.faculty_ids if x in faculty], "participant_group_ids": s.participant_group_ids})
    return {"id": table.id, "version": table.version, "status": table.status, "sessions": enriched}


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

