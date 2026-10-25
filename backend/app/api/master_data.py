from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.security import require_roles
from app.db.session import get_db
from app.models.entities import CourseOffering, Faculty, FacultyAvailability, FixedReservation, Room, RoomAvailability, SemesterOffering, TimetableSession, TimeSlot, User
from app.schemas.master_data import FacultyAvailabilitySlot, FacultyCreate, ReservationCreate, RoomAvailabilitySlot, RoomCreate

router = APIRouter(prefix="/api", tags=["Master Data"])


def page(db, model, page, page_size):
    total = db.scalar(select(func.count()).select_from(model)) or 0
    items = db.scalars(select(model).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/faculty")
def faculty_list(page_number: int = Query(1, alias="page", ge=1), page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "faculty", "student"))):
    return page(db, Faculty, page_number, page_size)


@router.post("/faculty", status_code=201)
def faculty_create(body: FacultyCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = Faculty(**body.model_dump()); db.add(item); db.commit(); db.refresh(item); return item


@router.put("/faculty/{item_id}")
def faculty_update(item_id: int, body: FacultyCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(Faculty, item_id)
    if not item: raise HTTPException(404, "Faculty record not found")
    for key, value in body.model_dump().items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item


@router.delete("/faculty/{item_id}", status_code=204)
def faculty_delete(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(Faculty, item_id)
    if not item: raise HTTPException(404, "Faculty record not found")
    used = any(item_id in (offering.faculty_ids or []) for offering in db.scalars(select(CourseOffering)).all())
    reserved = db.scalar(select(FixedReservation.id).where(FixedReservation.faculty_id == item_id).limit(1))
    has_login = db.scalar(select(User.id).where(User.faculty_id == item_id).limit(1))
    if used or reserved or has_login: raise HTTPException(409, "Faculty is assigned to a subject, reservation, or login. Remove those references first.")
    db.delete(item); db.commit(); return Response(status_code=204)


@router.get("/faculty/{item_id}/availability")
def faculty_availability(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if not db.get(Faculty, item_id): raise HTTPException(404, "Faculty record not found")
    items = db.scalars(select(FacultyAvailability).where(FacultyAvailability.faculty_id == item_id).order_by(FacultyAvailability.day, FacultyAvailability.period_index)).all()
    return {"items": items}


@router.put("/faculty/{item_id}/availability")
def replace_faculty_availability(item_id: int, body: list[FacultyAvailabilitySlot], db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    if not db.get(Faculty, item_id): raise HTTPException(404, "Faculty record not found")
    configured = {(slot.day, slot.period_index) for slot in db.scalars(select(TimeSlot)).all()}
    invalid = [(slot.day, slot.period_index) for slot in body if (slot.day, slot.period_index) not in configured]
    if invalid: raise HTTPException(422, {"invalid_time_slots": invalid})
    keys = [(slot.day, slot.period_index) for slot in body]
    if len(keys) != len(set(keys)): raise HTTPException(422, "Each day and period can appear only once")
    db.query(FacultyAvailability).filter(FacultyAvailability.faculty_id == item_id).delete()
    for slot in body:
        if not slot.available or slot.preference:
            db.add(FacultyAvailability(faculty_id=item_id, **slot.model_dump()))
    db.commit()
    return faculty_availability(item_id, db, user)


@router.get("/rooms")
def room_list(page_number: int = Query(1, alias="page", ge=1), page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "faculty", "student"))):
    return page(db, Room, page_number, page_size)


@router.post("/rooms", status_code=201)
def room_create(body: RoomCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = Room(**body.model_dump()); db.add(item); db.commit(); db.refresh(item); return item


@router.put("/rooms/{item_id}")
def room_update(item_id: int, body: RoomCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(Room, item_id)
    if not item: raise HTTPException(404, "Room record not found")
    for key, value in body.model_dump().items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item


@router.delete("/rooms/{item_id}", status_code=204)
def room_delete(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(Room, item_id)
    if not item: raise HTTPException(404, "Room record not found")
    used_by_offering = any(item_id in (offering.eligible_room_ids or []) or offering.fixed_room_id == item_id for offering in db.scalars(select(CourseOffering)).all())
    referenced = used_by_offering or db.scalar(select(SemesterOffering.id).where(SemesterOffering.home_room_id == item_id).limit(1)) or db.scalar(select(FixedReservation.id).where(FixedReservation.room_id == item_id).limit(1)) or db.scalar(select(TimetableSession.id).where(TimetableSession.room_id == item_id).limit(1))
    if referenced: raise HTTPException(409, "Room is used by a semester, subject, reservation, or generated timetable. Remove those references first.")
    db.delete(item); db.commit(); return Response(status_code=204)


@router.get("/rooms/{item_id}/availability")
def room_availability(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if not db.get(Room, item_id): raise HTTPException(404, "Room record not found")
    items = db.scalars(select(RoomAvailability).where(RoomAvailability.room_id == item_id).order_by(RoomAvailability.day, RoomAvailability.period_index)).all()
    return {"items": items}


@router.put("/rooms/{item_id}/availability")
def replace_room_availability(item_id: int, body: list[RoomAvailabilitySlot], db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if not db.get(Room, item_id): raise HTTPException(404, "Room record not found")
    configured = {(slot.day, slot.period_index) for slot in db.scalars(select(TimeSlot)).all()}
    invalid = [(slot.day, slot.period_index) for slot in body if (slot.day, slot.period_index) not in configured]
    if invalid: raise HTTPException(422, {"invalid_time_slots": invalid})
    keys = [(slot.day, slot.period_index) for slot in body]
    if len(keys) != len(set(keys)): raise HTTPException(422, "Each day and period can appear only once")
    db.query(RoomAvailability).filter(RoomAvailability.room_id == item_id).delete()
    for slot in body:
        if not slot.available or slot.note.strip():
            db.add(RoomAvailability(room_id=item_id, **slot.model_dump()))
    db.commit()
    return room_availability(item_id, db, _)


@router.get("/reservations")
def reservation_list(page_number: int = Query(1, alias="page", ge=1), page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    return page(db, FixedReservation, page_number, page_size)


@router.post("/reservations", status_code=201)
def reservation_create(body: ReservationCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = FixedReservation(**body.model_dump()); db.add(item); db.commit(); db.refresh(item); return item


@router.put("/reservations/{item_id}")
def reservation_update(item_id: int, body: ReservationCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(FixedReservation, item_id)
    if not item: raise HTTPException(404, "Reservation not found")
    for key, value in body.model_dump().items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item


@router.delete("/reservations/{item_id}", status_code=204)
def reservation_delete(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(FixedReservation, item_id)
    if not item: raise HTTPException(404, "Reservation not found")
    db.delete(item); db.commit(); return Response(status_code=204)

