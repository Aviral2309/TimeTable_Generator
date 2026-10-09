from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.security import require_roles
from app.db.session import get_db
from app.models.entities import AcademicYear, CourseOffering, Department, Faculty, FixedReservation, Institute, Room, SemesterOffering, TimeSlot, User
from app.schemas.setup import AcademicYearCreate, CourseOfferingCreate, DepartmentCreate, InstituteCreate, SemesterCreate, WorkingWeekCreate
from app.scheduling.database_problem import build_database_problem
from app.scheduling.preprocessing import validate_problem

router = APIRouter(prefix="/api/setup", tags=["Semester Preparation"])


@router.get("/status")
def setup_status(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    active_year = db.scalar(select(AcademicYear).where(AcademicYear.active.is_(True)).order_by(AcademicYear.id.desc()))
    semester_filter = SemesterOffering.academic_year_id == active_year.id if active_year else SemesterOffering.id < 0
    counts = {
        "institutes": db.scalar(select(func.count()).select_from(Institute)) or 0,
        "departments": db.scalar(select(func.count()).select_from(Department)) or 0,
        "academic_years": db.scalar(select(func.count()).select_from(AcademicYear).where(AcademicYear.active.is_(True))) or 0,
        "time_slots": db.scalar(select(func.count()).select_from(TimeSlot)) or 0,
        "faculty": db.scalar(select(func.count()).select_from(Faculty).where(Faculty.active.is_(True))) or 0,
        "rooms": db.scalar(select(func.count()).select_from(Room).where(Room.active.is_(True))) or 0,
        "semesters": db.scalar(select(func.count()).select_from(SemesterOffering).where(semester_filter)) or 0,
        "subjects": db.scalar(select(func.count()).select_from(CourseOffering).join(SemesterOffering).where(semester_filter)) or 0,
        "reservations": db.scalar(select(func.count()).select_from(FixedReservation)) or 0,
    }
    semesters_with_subjects = 0
    if active_year:
        configured = db.scalars(select(SemesterOffering).where(semester_filter)).all()
        semesters_with_subjects = sum(bool(db.scalar(select(CourseOffering.id).where(CourseOffering.semester_offering_id == item.id).limit(1))) for item in configured)
    steps = [
        {"key": "academic", "label": "Academic setup", "complete": counts["institutes"] > 0 and counts["departments"] > 0 and counts["academic_years"] > 0 and counts["time_slots"] > 0},
        {"key": "faculty", "label": "Faculty", "complete": counts["faculty"] > 0},
        {"key": "rooms", "label": "Rooms & laboratories", "complete": counts["rooms"] > 0},
        {"key": "semesters", "label": "Three semester cohorts", "complete": counts["semesters"] == 3},
        {"key": "subjects", "label": "Subjects & allocations", "complete": counts["semesters"] == 3 and semesters_with_subjects == 3},
    ]
    return {"counts": counts, "steps": steps, "ready_for_validation": all(step["complete"] for step in steps), "active_year": active_year}


@router.post("/institutes", status_code=201)
def create_institute(body: InstituteCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if db.scalar(select(Institute.id).limit(1)): raise HTTPException(409, "An institute is already configured")
    item = Institute(name=body.name.strip()); db.add(item); db.commit(); db.refresh(item); return item


@router.post("/departments", status_code=201)
def create_department(body: DepartmentCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = Department(code=body.code.strip().upper(), name=body.name.strip()); db.add(item); db.commit(); db.refresh(item); return item


@router.post("/academic-years", status_code=201)
def create_academic_year(body: AcademicYearCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    for year in db.scalars(select(AcademicYear)).all(): year.active = False
    item = AcademicYear(name=body.name.strip(), active=True); db.add(item); db.commit(); db.refresh(item); return item


@router.post("/working-week", status_code=201)
def create_working_week(body: WorkingWeekCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if db.scalar(select(TimeSlot.id).limit(1)): raise HTTPException(409, "Working hours are already configured")
    days = list(dict.fromkeys(day.strip().title() for day in body.days if day.strip()))
    if not days: raise HTTPException(422, "Select at least one working day")
    if body.lunch_after_period >= body.periods_per_day: raise HTTPException(422, "Lunch period must fall within the working day")
    if body.start_hour + body.periods_per_day > 24: raise HTTPException(422, "Working periods cannot extend past midnight")
    for day in days:
        for index in range(body.periods_per_day):
            start = body.start_hour + index
            db.add(TimeSlot(day=day, period_index=index, start_time=f"{start:02}:00", end_time=f"{start + 1:02}:00", blocked=index == body.lunch_after_period))
    db.commit()
    return {"created": len(days) * body.periods_per_day, "days": days}


@router.get("/options")
def options(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    return {
        "academic_years": db.scalars(select(AcademicYear).where(AcademicYear.active.is_(True))).all(),
        "departments": db.scalars(select(Department)).all(),
        "faculty": db.scalars(select(Faculty).where(Faculty.active.is_(True))).all(),
        "rooms": db.scalars(select(Room).where(Room.active.is_(True))).all(),
        "time_slots": db.scalars(select(TimeSlot).order_by(TimeSlot.day, TimeSlot.period_index)).all(),
    }


@router.get("/semesters")
def semesters(academic_year_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    items = db.scalars(select(SemesterOffering).where(SemesterOffering.academic_year_id == academic_year_id).order_by(SemesterOffering.semester_number)).all()
    return {"items": items}


@router.post("/semesters", status_code=201)
def create_semester(body: SemesterCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if not db.get(AcademicYear, body.academic_year_id): raise HTTPException(422, "Select a valid academic year")
    if not db.get(Department, body.department_id): raise HTTPException(422, "Select a valid department")
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
def validate_configuration(semester_ids: list[int], academic_year_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
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

