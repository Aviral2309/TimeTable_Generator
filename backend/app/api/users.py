from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, require_roles
from app.db.session import get_db
from app.models.entities import AcademicYear, Faculty, User
from app.api.auth import _student_groups
from app.schemas.auth import UserCreate, UserResponse, UserUpdate


router = APIRouter(prefix="/api/users", tags=["User Access"])


def _validate_links(db: Session, role: str, faculty_id: int | None, academic_year_id: int | None, student_group_id: str | None) -> None:
    if role == "faculty" and (not faculty_id or not db.get(Faculty, faculty_id)):
        raise HTTPException(422, "Select a valid faculty record")
    if role == "student":
        year = db.get(AcademicYear, academic_year_id) if academic_year_id else None
        groups = {group for row in (_student_groups(db, year.id) if year else []) for group in row["groups"]}
        if not year or not student_group_id or student_group_id not in groups:
            raise HTTPException(422, "Select a valid academic year, semester, and batch")


@router.get("")
def user_list(page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    total = db.scalar(select(func.count()).select_from(User)) or 0
    items = db.scalars(select(User).order_by(User.role, User.name).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [UserResponse.model_validate(item) for item in items], "total": total}


@router.post("", response_model=UserResponse, status_code=201)
def user_create(body: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    email = str(body.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "A login already exists for this email")
    _validate_links(db, body.role, body.faculty_id, body.academic_year_id, body.student_group_id)
    data = body.model_dump(exclude={"password"})
    data["email"] = email
    if body.role != "faculty": data["faculty_id"] = None
    if body.role != "student":
        data["academic_year_id"] = None
        data["student_group_id"] = None
    item = User(**data, password_hash=hash_password(body.password))
    db.add(item); db.commit(); db.refresh(item); return item


@router.put("/{item_id}", response_model=UserResponse)
def user_update(item_id: int, body: UserUpdate, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    item = db.get(User, item_id)
    if not item: raise HTTPException(404, "User account not found")
    email = str(body.email).lower()
    duplicate = db.scalar(select(User.id).where(User.email == email, User.id != item_id))
    if duplicate: raise HTTPException(409, "A login already exists for this email")
    _validate_links(db, body.role, body.faculty_id, body.academic_year_id, body.student_group_id)
    if actor.id == item.id and not body.active:
        raise HTTPException(409, "You cannot deactivate your own administrator account")
    data = body.model_dump(exclude={"password"})
    data["email"] = email
    if body.role != "faculty": data["faculty_id"] = None
    if body.role != "student":
        data["academic_year_id"] = None
        data["student_group_id"] = None
    for key, value in data.items(): setattr(item, key, value)
    if body.password: item.password_hash = hash_password(body.password)
    db.commit(); db.refresh(item); return item


@router.delete("/{item_id}", status_code=204)
def user_delete(item_id: int, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    item = db.get(User, item_id)
    if not item: raise HTTPException(404, "User account not found")
    if actor.id == item.id: raise HTTPException(409, "You cannot delete your own administrator account")
    db.delete(item); db.commit(); return Response(status_code=204)
