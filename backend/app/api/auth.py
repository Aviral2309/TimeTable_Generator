from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import create_token, get_current_user, hash_password, verify_password
from app.db.session import get_db
from app.models.entities import AcademicYear, CourseOffering, Faculty, Institute, SemesterOffering, User
from app.schemas.auth import BootstrapAdminRequest, LoginRequest, LoginResponse, PasswordChangeRequest, SelfRegistrationRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _student_groups(db: Session, academic_year_id: int) -> list[dict]:
    semesters = db.scalars(
        select(SemesterOffering)
        .where(SemesterOffering.academic_year_id == academic_year_id)
        .order_by(SemesterOffering.semester_number)
    ).all()
    rows = []
    for semester in semesters:
        offerings = db.scalars(select(CourseOffering).where(CourseOffering.semester_offering_id == semester.id)).all()
        prefix = f"SEM-{semester.semester_number}"
        groups = {prefix}
        groups.update(
            group
            for offering in offerings
            for group in (offering.participant_group_ids or [])
            if group == prefix or group.startswith(f"{prefix}-")
        )
        rows.append({"semester_number": semester.semester_number, "groups": sorted(groups)})
    return rows


@router.get("/bootstrap-status")
def bootstrap_status(db: Session = Depends(get_db)):
    return {
        "needs_admin": db.scalar(select(User.id).limit(1)) is None,
        "has_department_data": db.scalar(select(Institute.id).limit(1)) is not None,
    }


@router.get("/registration-options")
def registration_options(db: Session = Depends(get_db)):
    linked_faculty_ids = set(db.scalars(select(User.faculty_id).where(User.faculty_id.is_not(None))).all())
    faculty = db.scalars(select(Faculty).where(Faculty.active.is_(True)).order_by(Faculty.name)).all()
    years = db.scalars(select(AcademicYear).order_by(AcademicYear.name.desc(), AcademicYear.term_type)).all()
    return {
        "faculty": [
            {"id": item.id, "faculty_code": item.faculty_code, "name": item.name}
            for item in faculty if item.id not in linked_faculty_ids
        ],
        "academic_years": [
            {"id": year.id, "name": year.name, "term_type": year.term_type, "semesters": _student_groups(db, year.id)}
            for year in years
        ],
    }


@router.post("/register", status_code=201)
def self_register(body: SelfRegistrationRequest, db: Session = Depends(get_db)):
    email = str(body.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "An account already exists for this email")

    active = True
    name = body.name.strip()
    faculty_id = None
    academic_year_id = None
    student_group_id = None
    if body.role == "faculty":
        faculty = db.get(Faculty, body.faculty_id)
        if not faculty or not faculty.active:
            raise HTTPException(422, "Select an active faculty record")
        if faculty.email.lower() != email:
            raise HTTPException(422, "Use the SGSITS email stored in the selected faculty record")
        if db.scalar(select(User.id).where(User.faculty_id == faculty.id)):
            raise HTTPException(409, "This faculty record already has a login")
        name, faculty_id = faculty.name, faculty.id
    elif body.role == "student":
        year = db.get(AcademicYear, body.academic_year_id)
        valid_groups = {group for row in (_student_groups(db, year.id) if year else []) for group in row["groups"]}
        if not year or body.student_group_id not in valid_groups:
            raise HTTPException(422, "Select a valid academic year, semester, and batch")
        academic_year_id, student_group_id = year.id, body.student_group_id
    else:
        # The first administrator is activated immediately. Later administrator
        # requests remain inactive until an existing administrator approves them.
        active = db.scalar(select(User.id).where(User.role == "admin", User.active.is_(True)).limit(1)) is None

    user = User(
        email=email,
        name=name,
        password_hash=hash_password(body.password),
        role=body.role,
        faculty_id=faculty_id,
        academic_year_id=academic_year_id,
        student_group_id=student_group_id,
        active=active,
    )
    db.add(user); db.commit(); db.refresh(user)
    if not active:
        return {"pending_approval": True, "message": "Administrator request submitted. An active administrator must approve it before login."}
    return {"pending_approval": False, "access_token": create_token(user), "token_type": "bearer", "user": UserResponse.model_validate(user)}


@router.post("/bootstrap", response_model=LoginResponse, status_code=201)
def bootstrap_admin(body: BootstrapAdminRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User.id).limit(1)) is not None:
        raise HTTPException(409, "The first administrator has already been created")
    user = User(
        email=body.email.lower(),
        name=body.name.strip(),
        password_hash=hash_password(body.password),
        role="admin",
        active=True,
    )
    db.add(user); db.commit(); db.refresh(user)
    return LoginResponse(access_token=create_token(user), user=UserResponse.model_validate(user))


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower(), User.active.is_(True)))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    if body.role and user.role != body.role:
        raise HTTPException(403, f"This account is registered as {user.role}. Choose the {user.role.title()} workspace.")
    return LoginResponse(access_token=create_token(user), user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)): return user


@router.post("/change-password")
def change_password(body: PasswordChangeRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

