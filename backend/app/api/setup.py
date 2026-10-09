from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import require_roles
from app.db.session import get_db
from app.models.entities import AcademicYear, CourseOffering, Department, Faculty, Room, SemesterOffering, User
from app.schemas.setup import CourseOfferingCreate, SemesterCreate
from app.scheduling.database_problem import build_database_problem
from app.scheduling.preprocessing import validate_problem

router = APIRouter(prefix="/api/setup", tags=["Semester Preparation"])


@router.get("/options")
def options(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    return {
        "academic_years": db.scalars(select(AcademicYear).where(AcademicYear.active.is_(True))).all(),
        "departments": db.scalars(select(Department)).all(),
        "faculty": db.scalars(select(Faculty).where(Faculty.active.is_(True))).all(),
        "rooms": db.scalars(select(Room).where(Room.active.is_(True))).all(),
    }


@router.get("/semesters")
def semesters(academic_year_id: int = 1, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    items = db.scalars(select(SemesterOffering).where(SemesterOffering.academic_year_id == academic_year_id).order_by(SemesterOffering.semester_number)).all()
    return {"items": items}


@router.post("/semesters", status_code=201)
def create_semester(body: SemesterCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    room = db.get(Room, body.home_room_id)
    if not room or room.room_type != "theory" or room.capacity < body.strength:
        raise HTTPException(422, "Home classroom must be a theory room with sufficient capacity")
    item = SemesterOffering(**body.model_dump(), section="ALL"); db.add(item); db.commit(); db.refresh(item); return item


@router.get("/course-offerings")
def course_offerings(semester_offering_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    items = db.scalars(select(CourseOffering).where(CourseOffering.semester_offering_id == semester_offering_id).order_by(CourseOffering.code)).all()
    return {"items": items}


@router.post("/course-offerings", status_code=201)
def create_course_offering(body: CourseOfferingCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    semester = db.get(SemesterOffering, body.semester_offering_id)
    if not semester: raise HTTPException(404, "Semester configuration not found")
    missing_faculty = [x for x in body.faculty_ids if not db.get(Faculty, x)]
    missing_rooms = [x for x in body.eligible_room_ids if not db.get(Room, x)]
    if missing_faculty or missing_rooms: raise HTTPException(422, {"missing_faculty": missing_faculty, "missing_rooms": missing_rooms})
    data = body.model_dump(exclude={"participant_group"})
    data["participant_group_ids"] = [body.participant_group or f"SEM-{semester.semester_number}"]
    item = CourseOffering(**data); db.add(item); db.commit(); db.refresh(item); return item


@router.delete("/course-offerings/{offering_id}", status_code=204)
def delete_course_offering(offering_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(CourseOffering, offering_id)
    if not item: raise HTTPException(404, "Course offering not found")
    db.delete(item); db.commit()


@router.post("/validate")
def validate_configuration(semester_ids: list[int], academic_year_id: int = 1, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    semesters = db.scalars(select(SemesterOffering).where(SemesterOffering.id.in_(semester_ids))).all()
    errors: list[dict] = []
    if len(semester_ids) != 3:
        errors.append({"code": "semester_count", "message": "Select exactly three semester cohorts for joint generation."})
    if len({s.semester_number for s in semesters}) != len(semesters):
        errors.append({"code": "duplicate_semester", "message": "Each selected semester number must be unique; sections are not used."})
    for semester in semesters:
        if not db.scalar(select(CourseOffering.id).where(CourseOffering.semester_offering_id == semester.id).limit(1)):
            errors.append({"code": "missing_subjects", "message": f"Semester {semester.semester_number} has no subject offerings."})
    if not errors:
        try: errors.extend(validate_problem(build_database_problem(db, academic_year_id, semester_ids)))
        except ValueError as exc: errors.append({"code": "configuration", "message": str(exc)})
    return {"valid": not errors, "errors": errors, "semester_ids": semester_ids}

