from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.session import get_db
from app.models.entities import Faculty, RescheduleEvent, Room, Timetable, User
from app.schemas.rescheduling import RescheduleRequest
from app.services.rescheduling import ReschedulingError, apply_reschedule, plan_reschedule, public_plan


router = APIRouter(prefix="/api/rescheduling", tags=["Dynamic Rescheduling"])


@router.post("/preview")
def preview(request: RescheduleRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    try:
        return public_plan(plan_reschedule(db, request))
    except ReschedulingError as exc:
        raise HTTPException(422, exc.detail) from exc


@router.post("/apply")
def apply(request: RescheduleRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    try:
        return apply_reschedule(db, request, user.id)
    except ReschedulingError as exc:
        db.rollback()
        raise HTTPException(409, exc.detail) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, f"Rescheduling failed: {exc}") from exc


@router.get("/history")
def history(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    events = db.scalars(select(RescheduleEvent).order_by(desc(RescheduleEvent.id)).limit(50)).all()
    faculty_ids = {event.resource_id for event in events if event.resource_type == "faculty"}
    room_ids = {event.resource_id for event in events if event.resource_type == "room"}
    faculty = {item.id: item for item in db.scalars(select(Faculty).where(Faculty.id.in_(faculty_ids))).all()} if faculty_ids else {}
    rooms = {item.id: item for item in db.scalars(select(Room).where(Room.id.in_(room_ids))).all()} if room_ids else {}
    timetable_ids = {event.source_timetable_id for event in events} | {event.result_timetable_id for event in events if event.result_timetable_id}
    timetables = {item.id: item for item in db.scalars(select(Timetable).where(Timetable.id.in_(timetable_ids))).all()} if timetable_ids else {}
    return {"items": [{
        "id": event.id,
        "source_timetable_id": event.source_timetable_id,
        "source_version": timetables[event.source_timetable_id].version if event.source_timetable_id in timetables else None,
        "result_timetable_id": event.result_timetable_id,
        "result_version": timetables[event.result_timetable_id].version if event.result_timetable_id in timetables else None,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "resource_name": (
            f"{faculty[event.resource_id].faculty_code} · {faculty[event.resource_id].name}"
            if event.resource_type == "faculty" and event.resource_id in faculty
            else f"{rooms[event.resource_id].code} · {rooms[event.resource_id].name}"
            if event.resource_type == "room" and event.resource_id in rooms
            else f"{event.resource_type.title()} {event.resource_id}"
        ),
        "day": event.day,
        "start_period": event.start_period,
        "duration_periods": event.duration_periods,
        "reason": event.reason,
        "status": event.status,
        "affected_sessions": event.affected_sessions,
        "moved_sessions": event.moved_sessions,
        "created_at": event.created_at,
    } for event in events]}
