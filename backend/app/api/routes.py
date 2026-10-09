from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
import csv
import io
from app.core.security import require_roles
from app.db.session import get_db
from app.models.entities import GenerationRun, Timetable, TimetableSession, User
from app.schemas.generation import GenerationRequest, GenerationResponse
from app.services.generation import generate_demo

router = APIRouter(prefix="/api")


@router.get("/health")
def health(): return {"status": "ok"}


@router.post("/generation/demo", response_model=GenerationResponse)
def generate(request: GenerationRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    try:
        return generate_demo(db, request.academic_year_id, request.solver_mode, request.time_limit_seconds, request.random_seed)
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
    return {"id": table.id, "version": table.version, "status": table.status, "sessions": sessions}


@router.get("/export/latest.csv")
def export_latest(db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "faculty", "student"))):
    data = latest_timetable(db, user)
    stream = io.StringIO(); writer = csv.writer(stream)
    writer.writerow(["day", "start_period", "duration", "course_offering_id", "room_id", "faculty_ids", "participant_groups"])
    for s in data["sessions"]:
        writer.writerow([s.day, s.start_period, s.duration_periods, s.course_offering_id, s.room_id, ";".join(map(str, s.faculty_ids)), ";".join(s.participant_group_ids)])
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=timetable.csv"})


@router.get("/analytics/summary")
def analytics(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    runs = db.scalars(select(GenerationRun).order_by(desc(GenerationRun.id)).limit(10)).all()
    return {"recent_runs": [{"id": r.id, "status": r.status, "mode": r.solver_mode, "runtime": r.runtime_seconds, "objective": r.objective_value} for r in runs], "successful_runs": sum(r.status in {"optimal", "feasible"} for r in runs)}

