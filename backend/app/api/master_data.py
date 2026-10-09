from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.security import require_roles
from app.db.session import get_db
from app.models.entities import Faculty, FixedReservation, Room, User
from app.schemas.master_data import FacultyCreate, ReservationCreate, RoomCreate

router = APIRouter(prefix="/api", tags=["Master Data"])


def page(db, model, page, page_size):
    total = db.scalar(select(func.count()).select_from(model)) or 0
    items = db.scalars(select(model).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/faculty")
def faculty_list(page_number: int = Query(1, alias="page", ge=1), page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "faculty"))):
    return page(db, Faculty, page_number, page_size)


@router.post("/faculty", status_code=201)
def faculty_create(body: FacultyCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = Faculty(**body.model_dump()); db.add(item); db.commit(); db.refresh(item); return item


@router.get("/rooms")
def room_list(page_number: int = Query(1, alias="page", ge=1), page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "faculty", "student"))):
    return page(db, Room, page_number, page_size)


@router.post("/rooms", status_code=201)
def room_create(body: RoomCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = Room(**body.model_dump()); db.add(item); db.commit(); db.refresh(item); return item


@router.get("/reservations")
def reservation_list(page_number: int = Query(1, alias="page", ge=1), page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    return page(db, FixedReservation, page_number, page_size)


@router.post("/reservations", status_code=201)
def reservation_create(body: ReservationCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = FixedReservation(**body.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

