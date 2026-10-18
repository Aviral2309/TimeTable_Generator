from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
import re
from app.core.security import require_roles
from app.db.session import get_db
from app.models.entities import AcademicYear, CourseOffering, Department, Faculty, FacultyAvailability, FixedReservation, GenerationRun, Institute, Room, SemesterOffering, TimeSlot, TimetableSession, User
from app.schemas.setup import AcademicYearCreate, CourseOfferingCreate, DemoDataCreate, DepartmentCreate, InstituteCreate, LabOfferingBatchCreate, SemesterCreate, TermCohortsCreate, WorkingWeekCreate
from app.scheduling.database_problem import build_database_problem
from app.scheduling.preprocessing import validate_problem

router = APIRouter(prefix="/api/setup", tags=["Semester Preparation"])

TERM_SEMESTERS = {"odd": {3, 5, 7}, "even": {2, 4, 6}}


def participant_groups_for(body: CourseOfferingCreate, semester: SemesterOffering) -> list[str]:
    if body.kind == "elective" and body.parallel_elective:
        code = re.sub(r"[^A-Za-z0-9]+", "-", body.code.strip()).strip("-").upper()
        return [f"SEM-{semester.semester_number}-ELECTIVE-{code}"]
    return [body.participant_group or f"SEM-{semester.semester_number}"]


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
    configured = []
    if active_year:
        configured = db.scalars(select(SemesterOffering).where(semester_filter)).all()
        semesters_with_subjects = sum(bool(db.scalar(select(CourseOffering.id).where(CourseOffering.semester_offering_id == item.id).limit(1))) for item in configured)
    steps = [
        {"key": "academic", "label": "Academic setup", "complete": counts["institutes"] > 0 and counts["departments"] > 0 and counts["academic_years"] > 0 and counts["time_slots"] > 0},
        {"key": "faculty", "label": "Faculty", "complete": counts["faculty"] > 0},
        {"key": "rooms", "label": "Rooms & laboratories", "complete": counts["rooms"] > 0},
        {"key": "semesters", "label": f"{(active_year.term_type if active_year else 'odd').title()} term semesters", "complete": bool(active_year) and {s.semester_number for s in configured} == TERM_SEMESTERS[active_year.term_type]},
        {"key": "subjects", "label": "Subjects & allocations", "complete": bool(active_year) and {s.semester_number for s in configured} == TERM_SEMESTERS[active_year.term_type] and semesters_with_subjects == 3},
    ]
    readiness_issues: list[dict] = []
    category_complete = all(step["complete"] for step in steps)
    if category_complete and active_year:
        try:
            problem = build_database_problem(db, active_year.id, [semester.id for semester in configured])
            readiness_issues = validate_problem(problem)
        except ValueError as exc:
            readiness_issues = [{"code": "configuration", "message": str(exc)}]
    return {
        "counts": counts,
        "steps": steps,
        "ready_for_validation": category_complete and not readiness_issues,
        "readiness_issues": readiness_issues[:20],
        "active_year": active_year,
    }


@router.post("/institutes", status_code=201)
def create_institute(body: InstituteCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if db.scalar(select(Institute.id).limit(1)): raise HTTPException(409, "An institute is already configured")
    item = Institute(name=body.name.strip()); db.add(item); db.commit(); db.refresh(item); return item


@router.put("/institutes/{item_id}")
def update_institute(item_id: int, body: InstituteCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(Institute, item_id)
    if not item: raise HTTPException(404, "Institute not found")
    item.name = body.name.strip(); db.commit(); db.refresh(item); return item


@router.delete("/institutes/{item_id}", status_code=204)
def delete_institute(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(Institute, item_id)
    if not item: raise HTTPException(404, "Institute not found")
    db.delete(item); db.commit(); return Response(status_code=204)


@router.post("/departments", status_code=201)
def create_department(body: DepartmentCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = Department(code=body.code.strip().upper(), name=body.name.strip()); db.add(item); db.commit(); db.refresh(item); return item


@router.put("/departments/{item_id}")
def update_department(item_id: int, body: DepartmentCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(Department, item_id)
    if not item: raise HTTPException(404, "Department not found")
    item.code = body.code.strip().upper(); item.name = body.name.strip(); db.commit(); db.refresh(item); return item


@router.delete("/departments/{item_id}", status_code=204)
def delete_department(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(Department, item_id)
    if not item: raise HTTPException(404, "Department not found")
    referenced = db.scalar(select(Faculty.id).where(Faculty.home_department_id == item_id).limit(1)) or db.scalar(select(Room.id).where(Room.department_id == item_id).limit(1)) or db.scalar(select(SemesterOffering.id).where(SemesterOffering.department_id == item_id).limit(1))
    if referenced: raise HTTPException(409, "Department is used by faculty, rooms, or semesters. Remove those records first.")
    db.delete(item); db.commit(); return Response(status_code=204)


@router.get("/academic-years")
def academic_years(db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "faculty", "student"))):
    return {"items": db.scalars(select(AcademicYear).order_by(AcademicYear.name.desc(), AcademicYear.term_type)).all()}


@router.post("/academic-years", status_code=201)
def create_academic_year(body: AcademicYearCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    for year in db.scalars(select(AcademicYear)).all(): year.active = False
    item = AcademicYear(name=body.name.strip(), term_type=body.term_type, active=True); db.add(item); db.commit(); db.refresh(item); return item


@router.post("/academic-years/{item_id}/activate")
def activate_academic_year(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(AcademicYear, item_id)
    if not item: raise HTTPException(404, "Academic term not found")
    for year in db.scalars(select(AcademicYear)).all(): year.active = year.id == item_id
    db.commit(); db.refresh(item); return item


@router.put("/academic-years/{item_id}")
def update_academic_year(item_id: int, body: AcademicYearCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(AcademicYear, item_id)
    if not item: raise HTTPException(404, "Academic year not found")
    existing_semesters = db.scalars(select(SemesterOffering).where(SemesterOffering.academic_year_id == item_id)).all()
    if existing_semesters and any(s.semester_number not in TERM_SEMESTERS[body.term_type] for s in existing_semesters):
        raise HTTPException(409, "Remove semesters that do not belong to the selected Odd/Even term before changing it")
    item.name = body.name.strip(); item.term_type = body.term_type; db.commit(); db.refresh(item); return item


@router.delete("/academic-years/{item_id}", status_code=204)
def delete_academic_year(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(AcademicYear, item_id)
    if not item: raise HTTPException(404, "Academic year not found")
    referenced = db.scalar(select(SemesterOffering.id).where(SemesterOffering.academic_year_id == item_id).limit(1)) or db.scalar(select(FixedReservation.id).where(FixedReservation.academic_year_id == item_id).limit(1)) or db.scalar(select(GenerationRun.id).where(GenerationRun.academic_year_id == item_id).limit(1))
    if referenced: raise HTTPException(409, "Academic year has semesters, reservations, or generation runs. Remove those records first.")
    db.delete(item); db.commit(); return Response(status_code=204)


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


@router.put("/working-week")
def update_working_week(body: WorkingWeekCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    days = [day.strip() for day in body.days if day.strip()]
    if not days: raise HTTPException(422, "Select at least one working day")
    if body.lunch_after_period >= body.periods_per_day: raise HTTPException(422, "Lunch period must fall within the working day")
    if body.start_hour + body.periods_per_day > 24: raise HTTPException(422, "Working periods cannot extend past midnight")
    db.query(TimeSlot).delete(); db.commit()
    return create_working_week(body, db, _)


@router.delete("/working-week", status_code=204)
def delete_working_week(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    db.query(TimeSlot).delete(); db.commit(); return Response(status_code=204)


@router.get("/options")
def options(db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "faculty", "student"))):
    return {
        "institutes": db.scalars(select(Institute).order_by(Institute.id)).all(),
        "academic_years": db.scalars(select(AcademicYear).order_by(AcademicYear.name.desc(), AcademicYear.term_type)).all(),
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
    year = db.get(AcademicYear, body.academic_year_id)
    if not year: raise HTTPException(422, "Select a valid academic year")
    if body.semester_number not in TERM_SEMESTERS[year.term_type]: raise HTTPException(422, f"{year.term_type.title()} term allows semesters {sorted(TERM_SEMESTERS[year.term_type])}")
    if not db.get(Department, body.department_id): raise HTTPException(422, "Select a valid department")
    room = db.get(Room, body.home_room_id) if body.home_room_id else None
    if body.home_room_id and (not room or room.room_type != "theory" or room.capacity < body.strength):
        raise HTTPException(422, "Home classroom must be a theory room with sufficient capacity")
    item = SemesterOffering(**body.model_dump(), section="ALL"); db.add(item); db.commit(); db.refresh(item); return item


@router.put("/semesters/{item_id}")
def update_semester(item_id: int, body: SemesterCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(SemesterOffering, item_id)
    if not item: raise HTTPException(404, "Semester configuration not found")
    year = db.get(AcademicYear, body.academic_year_id)
    if not year or body.semester_number not in TERM_SEMESTERS[year.term_type]: raise HTTPException(422, "Semester does not belong to the selected Odd/Even term")
    room = db.get(Room, body.home_room_id) if body.home_room_id else None
    if body.home_room_id and (not room or room.room_type != "theory" or room.capacity < body.strength): raise HTTPException(422, "Home classroom must be a theory room with sufficient capacity")
    for key, value in body.model_dump().items(): setattr(item, key, value)
    item.section = "ALL"; db.commit(); db.refresh(item); return item


@router.delete("/semesters/{item_id}", status_code=204)
def delete_semester(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(SemesterOffering, item_id)
    if not item: raise HTTPException(404, "Semester configuration not found")
    offerings = db.scalars(select(CourseOffering).where(CourseOffering.semester_offering_id == item_id)).all()
    offering_ids = [offering.id for offering in offerings]
    if offering_ids and db.scalar(select(TimetableSession.id).where(TimetableSession.course_offering_id.in_(offering_ids)).limit(1)):
        raise HTTPException(409, "Semester is used by a generated timetable. Generate a new version or clear that timetable first.")
    for offering in offerings: db.delete(offering)
    db.delete(item); db.commit(); return Response(status_code=204)


@router.post("/term-cohorts", status_code=201)
def create_term_cohorts(body: TermCohortsCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    year = db.get(AcademicYear, body.academic_year_id)
    if not year: raise HTTPException(422, "Select a valid academic term")
    if not db.get(Department, body.department_id): raise HTTPException(422, "Select a valid department")
    existing = {item.semester_number for item in db.scalars(select(SemesterOffering).where(SemesterOffering.academic_year_id == year.id, SemesterOffering.department_id == body.department_id)).all()}
    for semester_number in sorted(TERM_SEMESTERS[year.term_type] - existing):
        db.add(SemesterOffering(academic_year_id=year.id, department_id=body.department_id, semester_number=semester_number, section="ALL", strength=body.default_strength, home_room_id=None, home_room_policy="disabled"))
    db.commit()
    return semesters(year.id, db, _)


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
    data["participant_group_ids"] = participant_groups_for(body, semester)
    item = CourseOffering(**data); db.add(item); db.commit(); db.refresh(item); return item


@router.post("/course-offerings/lab-batches", status_code=201)
def create_lab_batch_offerings(body: LabOfferingBatchCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    semester = db.get(SemesterOffering, body.semester_offering_id)
    if not semester:
        raise HTTPException(404, "Semester configuration not found")
    faculty_ids = {faculty_id for batch in body.batches for faculty_id in batch.faculty_ids}
    room_ids = {batch.room_id for batch in body.batches if batch.room_id is not None}
    missing_faculty = [faculty_id for faculty_id in faculty_ids if not db.get(Faculty, faculty_id)]
    rooms = {room_id: db.get(Room, room_id) for room_id in room_ids}
    missing_rooms = [room_id for room_id, room in rooms.items() if not room]
    non_lab_rooms = [room_id for room_id, room in rooms.items() if room and room.room_type != "lab"]
    if missing_faculty or missing_rooms or non_lab_rooms:
        raise HTTPException(422, {
            "missing_faculty": missing_faculty,
            "missing_rooms": missing_rooms,
            "non_lab_rooms": non_lab_rooms,
        })

    base_size, remainder = divmod(body.total_enrollment, len(body.batches))
    items = []
    for index, batch in enumerate(body.batches):
        group = " ".join(batch.participant_group.strip().split())
        if not group.casefold().startswith("sem-"):
            group = f"SEM-{semester.semester_number}-{group}"
        room_ids_for_batch = [batch.room_id] if batch.room_id is not None else []
        item = CourseOffering(
            semester_offering_id=semester.id,
            code=body.code.strip(),
            name=body.name.strip(),
            kind="lab",
            sessions_per_week=body.sessions_per_week,
            duration_periods=2,
            enrollment=base_size + (1 if index < remainder else 0),
            faculty_ids=batch.faculty_ids,
            participant_group_ids=[group],
            eligible_room_ids=room_ids_for_batch,
            required_features=body.required_features,
            elective_group=None,
            parallel_elective=False,
            fixed_day=None,
            fixed_period=None,
            fixed_room_id=batch.room_id,
        )
        db.add(item)
        items.append(item)
    db.commit()
    for item in items:
        db.refresh(item)
    return {"items": items, "batch_count": len(items), "elective_lab": body.elective_lab}


@router.put("/course-offerings/{offering_id}")
def update_course_offering(offering_id: int, body: CourseOfferingCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(CourseOffering, offering_id)
    if not item: raise HTTPException(404, "Course offering not found")
    semester = db.get(SemesterOffering, body.semester_offering_id)
    if not semester: raise HTTPException(404, "Semester configuration not found")
    missing_faculty = [x for x in body.faculty_ids if not db.get(Faculty, x)]
    missing_rooms = [x for x in body.eligible_room_ids if not db.get(Room, x)]
    if missing_faculty or missing_rooms: raise HTTPException(422, {"missing_faculty": missing_faculty, "missing_rooms": missing_rooms})
    data = body.model_dump(exclude={"participant_group"}); data["participant_group_ids"] = participant_groups_for(body, semester)
    for key, value in data.items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item


@router.delete("/course-offerings/{offering_id}", status_code=204)
def delete_course_offering(offering_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    item = db.get(CourseOffering, offering_id)
    if not item: raise HTTPException(404, "Course offering not found")
    if db.scalar(select(TimetableSession.id).where(TimetableSession.course_offering_id == offering_id).limit(1)):
        raise HTTPException(409, "Subject is used by a generated timetable and cannot be deleted.")
    db.delete(item); db.commit(); return Response(status_code=204)


@router.post("/validate")
def validate_configuration(semester_ids: list[int], academic_year_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    semesters = db.scalars(select(SemesterOffering).where(SemesterOffering.id.in_(semester_ids))).all()
    errors: list[dict] = []
    year = db.get(AcademicYear, academic_year_id)
    expected = TERM_SEMESTERS.get(year.term_type, set()) if year else set()
    if not year:
        errors.append({"code": "academic_year", "message": "Select a valid academic term."})
    elif {s.semester_number for s in semesters} != expected:
        errors.append({"code": "semester_set", "message": f"{year.term_type.title()} term must contain semesters {', '.join(map(str, sorted(expected)))}."})
    if len({s.semester_number for s in semesters}) != len(semesters):
        errors.append({"code": "duplicate_semester", "message": "Each selected semester number must be unique; sections are not used."})
    for semester in semesters:
        if not db.scalar(select(CourseOffering.id).where(CourseOffering.semester_offering_id == semester.id).limit(1)):
            errors.append({"code": "missing_subjects", "message": f"Semester {semester.semester_number} has no subject offerings."})
        parallel = db.scalars(select(CourseOffering).where(
            CourseOffering.semester_offering_id == semester.id,
            CourseOffering.parallel_elective.is_(True),
        )).all()
        by_group: dict[str, list[CourseOffering]] = {}
        for offering in parallel:
            by_group.setdefault(offering.elective_group or "", []).append(offering)
        for elective_group, alternatives in by_group.items():
            used_groups: set[str] = set()
            duplicate_groups: set[str] = set()
            for alternative in alternatives:
                for participant_group in alternative.participant_group_ids or []:
                    if participant_group in used_groups:
                        duplicate_groups.add(participant_group)
                    used_groups.add(participant_group)
            if duplicate_groups:
                errors.append({
                    "code": "parallel_elective_group_collision",
                    "message": f"Semester {semester.semester_number} elective group {elective_group} reuses student group(s) {', '.join(sorted(duplicate_groups))}. Each simultaneous alternative needs its own student group.",
                })
    if not errors:
        try: errors.extend(validate_problem(build_database_problem(db, academic_year_id, semester_ids)))
        except ValueError as exc: errors.append({"code": "configuration", "message": str(exc)})
    return {"valid": not errors, "errors": errors, "semester_ids": semester_ids}


@router.post("/demo-data", status_code=201)
def create_demo_data(body: DemoDataCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    populated = any(db.scalar(select(func.count()).select_from(model)) for model in (Institute, Department, AcademicYear, Faculty, Room, TimeSlot, SemesterOffering))
    if populated: raise HTTPException(409, "Demo data can only be loaded into an empty academic setup")

    institute = Institute(name="Shri G. S. Institute of Technology & Science, Indore")
    electrical = Department(code="EE", name="Electrical Engineering")
    humanities = Department(code="HU", name="Humanities")
    science = Department(code="AS", name="Applied Sciences")
    year = AcademicYear(name=f"2026-27 {body.term_type.title()}", term_type=body.term_type, active=True)
    db.add_all([institute, electrical, humanities, science, year]); db.flush()

    faculty_specs = [
        ("AD", "Dr. A. Deshmukh", electrical.id), ("SS", "Dr. S. Sharma", electrical.id),
        ("HKV", "Dr. H. K. Verma", electrical.id), ("AP", "Prof. A. Patel", electrical.id),
        ("RR", "Dr. R. Rao", electrical.id), ("UV", "Prof. U. Verma", electrical.id),
        ("SG", "Dr. S. Gupta", electrical.id), ("MPSC", "Prof. M. P. Singh", electrical.id),
        ("HUM", "Dr. N. Joshi", humanities.id), ("PHY", "Dr. P. Mehta", science.id),
    ]
    teachers = []
    for code, name, department_id in faculty_specs:
        teacher = Faculty(faculty_code=code, name=name, email=f"{code.lower()}@demo.edu", home_department_id=department_id, weekly_limit=18, daily_limit=6, max_consecutive=3)
        db.add(teacher); teachers.append(teacher)
    db.flush()
    by_code = {teacher.faculty_code: teacher for teacher in teachers}

    room_specs = [
        ("201", "Semester Classroom 201", "theory", 80, []),
        ("205", "Semester Classroom 205", "theory", 80, []),
        ("207", "Semester Classroom 207", "theory", 80, []),
        ("EEL-1", "Electrical Machines Laboratory", "lab", 32, ["machines"]),
        ("EEL-2", "Power Electronics Laboratory", "lab", 32, ["power-benches"]),
        ("COMP-LAB", "Computer Laboratory", "lab", 32, ["computers"]),
    ]
    rooms = []
    for code, name, kind, capacity, features in room_specs:
        room = Room(code=code, name=name, department_id=electrical.id, capacity=capacity, room_type=kind, features=features)
        db.add(room); rooms.append(room)
    db.flush()
    theory_rooms = rooms[:3]; lab_rooms = rooms[3:]

    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]:
        for index in range(8):
            hour = 9 + index
            db.add(TimeSlot(day=day, period_index=index, start_time=f"{hour:02}:00", end_time=f"{hour + 1:02}:00", blocked=index == 3))

    semesters = []
    for index, semester_number in enumerate(sorted(TERM_SEMESTERS[body.term_type])):
        semester = SemesterOffering(academic_year_id=year.id, department_id=electrical.id, semester_number=semester_number, section="ALL", strength=60, home_room_id=theory_rooms[index].id, home_room_policy="hard")
        db.add(semester); semesters.append(semester)
    db.flush()

    teacher_pairs = [("AD", "SS"), ("HKV", "AP"), ("RR", "UV")]
    for index, semester in enumerate(semesters):
        number = semester.semester_number
        primary, secondary = teacher_pairs[index]
        common = dict(semester_offering_id=semester.id, enrollment=60, participant_group_ids=[f"SEM-{number}"], eligible_room_ids=[semester.home_room_id], required_features=[])
        db.add(CourseOffering(code=f"EE{number}01", name="Electrical Engineering Core I", kind="theory", sessions_per_week=3, duration_periods=1, faculty_ids=[by_code[primary].id], **common))
        db.add(CourseOffering(code=f"EE{number}02", name="Electrical Engineering Core II", kind="theory", sessions_per_week=3, duration_periods=1, faculty_ids=[by_code[primary].id, by_code[secondary].id], **common))
        db.add(CourseOffering(semester_offering_id=semester.id, code=f"EE{number}L1", name="Electrical Engineering Laboratory", kind="lab", sessions_per_week=1, duration_periods=2, enrollment=30, faculty_ids=[by_code[secondary].id], participant_group_ids=[f"SEM-{number}-B1"], eligible_room_ids=[lab_rooms[index % len(lab_rooms)].id], required_features=[]))

    senior = semesters[-1]
    for offset, (code, teacher_code) in enumerate([("EL-A", "SG"), ("EL-B", "MPSC"), ("EL-C", "HUM")], 1):
        db.add(CourseOffering(semester_offering_id=senior.id, code=f"{code}{senior.semester_number}", name=f"Elective Option {offset}", kind="elective", sessions_per_week=2, duration_periods=1, enrollment=20, faculty_ids=[by_code[teacher_code].id], participant_group_ids=[f"SEM-{senior.semester_number}-E{offset}"], eligible_room_ids=[room.id for room in theory_rooms], required_features=[], elective_group=f"SEM-{senior.semester_number}-ELECTIVE", parallel_elective=True))

    first_year_lab = lab_rooms[0]
    db.add(FixedReservation(academic_year_id=year.id, day="Monday", start_period=0, duration_periods=2, room_id=first_year_lab.id, participant_group_id="FIRST-YEAR-EE", description="Fixed first-year Electrical Engineering laboratory"))
    for teacher_code, day, periods in [("HUM", "Monday", [0, 1, 2]), ("PHY", "Friday", [4, 5, 6, 7])]:
        for period in periods:
            db.add(FacultyAvailability(faculty_id=by_code[teacher_code].id, day=day, period_index=period, available=False, preference=0))
    db.commit()
    return {"loaded": True, "term_type": body.term_type, "semester_numbers": sorted(TERM_SEMESTERS[body.term_type]), "faculty": len(teachers), "rooms": len(rooms)}

