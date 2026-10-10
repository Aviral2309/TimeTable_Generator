from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import bootstrap_admin, bootstrap_status
from app.api.master_data import faculty_availability, faculty_create, faculty_delete, faculty_update, replace_faculty_availability, reservation_create, reservation_delete, reservation_update, room_create, room_delete, room_update
from app.api.setup import create_academic_year, create_course_offering, create_demo_data, create_department, create_institute, create_semester, create_working_week, delete_course_offering, delete_semester, setup_status, update_course_offering, update_semester, validate_configuration
from app.db.session import Base
from app.models.entities import AcademicYear, CourseOffering, Faculty, FixedReservation, SemesterOffering, User
from app.schemas.auth import BootstrapAdminRequest
from app.schemas.master_data import FacultyAvailabilitySlot, FacultyCreate, ReservationCreate, RoomCreate
from app.schemas.setup import AcademicYearCreate, CourseOfferingCreate, DemoDataCreate, DepartmentCreate, InstituteCreate, SemesterCreate, WorkingWeekCreate


def empty_database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_empty_installation_bootstraps_only_the_first_admin():
    db = empty_database()
    assert bootstrap_status(db)["needs_admin"] is True
    response = bootstrap_admin(BootstrapAdminRequest(name="System Admin", email="admin@college.edu", password="strong-pass"), db)
    assert response.user.role == "admin"
    assert bootstrap_status(db)["needs_admin"] is False
    assert db.query(User).count() == 1


def test_setup_status_starts_empty_and_tracks_admin_foundation():
    db = empty_database()
    actor = User(email="admin@college.edu", name="Admin", password_hash="x", role="admin")
    initial = setup_status(db, actor)
    assert initial["ready_for_validation"] is False
    assert all(value == 0 for value in initial["counts"].values())

    create_institute(InstituteCreate(name="Example Institute"), db, actor)
    create_department(DepartmentCreate(code="EE", name="Electrical Engineering"), db, actor)
    create_academic_year(AcademicYearCreate(name="2026-27"), db, actor)
    create_working_week(WorkingWeekCreate(days=["Monday", "Tuesday"], start_hour=10, periods_per_day=6, lunch_after_period=3), db, actor)

    configured = setup_status(db, actor)
    assert configured["counts"]["time_slots"] == 12
    assert configured["steps"][0]["complete"] is True
    assert configured["ready_for_validation"] is False


def test_admin_can_create_update_and_delete_operational_records():
    db = empty_database(); actor = User(email="admin@college.edu", name="Admin", password_hash="x", role="admin")
    create_institute(InstituteCreate(name="Example Institute"), db, actor)
    department = create_department(DepartmentCreate(code="EE", name="Electrical Engineering"), db, actor)
    year = create_academic_year(AcademicYearCreate(name="2026-27"), db, actor)
    create_working_week(WorkingWeekCreate(days=["Monday", "Tuesday"], start_hour=10, periods_per_day=6, lunch_after_period=3), db, actor)
    faculty_body = FacultyCreate(faculty_code="F01", name="Teacher One", email="one@example.edu", home_department_id=department.id)
    faculty = faculty_create(faculty_body, db, actor)
    faculty = faculty_update(faculty.id, faculty_body.model_copy(update={"name": "Teacher Updated"}), db, actor)
    assert faculty.name == "Teacher Updated"
    room_body = RoomCreate(code="R1", name="Room One", department_id=department.id, capacity=70, room_type="theory", features=["projector"])
    room = room_create(room_body, db, actor)
    room = room_update(room.id, room_body.model_copy(update={"name": "Room Updated"}), db, actor)
    assert room.name == "Room Updated"
    reservation_body = ReservationCreate(academic_year_id=year.id, day="Monday", start_period=0, duration_periods=1, room_id=room.id, description="Meeting")
    reservation = reservation_create(reservation_body, db, actor)
    assert reservation_update(reservation.id, reservation_body.model_copy(update={"description": "Updated meeting"}), db, actor).description == "Updated meeting"
    reservation_delete(reservation.id, db, actor)
    semester_body = SemesterCreate(academic_year_id=year.id, department_id=department.id, semester_number=3, strength=60, home_room_id=room.id)
    semester = create_semester(semester_body, db, actor)
    assert update_semester(semester.id, semester_body.model_copy(update={"strength": 55}), db, actor).strength == 55
    course_body = CourseOfferingCreate(semester_offering_id=semester.id, code="EE301", name="Networks", kind="theory", sessions_per_week=3, duration_periods=1, enrollment=55, faculty_ids=[faculty.id], eligible_room_ids=[room.id])
    course = create_course_offering(course_body, db, actor)
    assert update_course_offering(course.id, course_body.model_copy(update={"name": "Network Theory"}), db, actor).name == "Network Theory"
    delete_course_offering(course.id, db, actor); delete_semester(semester.id, db, actor)
    faculty_delete(faculty.id, db, actor); room_delete(room.id, db, actor)


def test_demo_data_supports_terms_electives_coteaching_and_constraints():
    db = empty_database(); actor = User(email="admin@college.edu", name="Admin", password_hash="x", role="admin")
    result = create_demo_data(DemoDataCreate(term_type="even"), db, actor)
    assert result["semester_numbers"] == [2, 4, 6]
    year = db.query(AcademicYear).one()
    assert year.term_type == "even"
    assert {item.semester_number for item in db.query(SemesterOffering).all()} == {2, 4, 6}
    electives = db.query(CourseOffering).filter(CourseOffering.kind == "elective").all()
    assert len(electives) == 3
    assert len({item.elective_group for item in electives}) == 1
    assert all(item.parallel_elective for item in electives)
    assert any(len(item.faculty_ids) > 1 for item in db.query(CourseOffering).all())
    reservation = db.query(FixedReservation).one()
    assert reservation.participant_group_id == "FIRST-YEAR-EE"
    assert reservation.duration_periods == 2
    external_teacher = db.query(Faculty).filter(Faculty.faculty_code == "HUM").one()
    assert faculty_availability(external_teacher.id, db, actor)["items"]
    replaced = replace_faculty_availability(external_teacher.id, [FacultyAvailabilitySlot(day="Tuesday", period_index=2, available=False)], db, actor)
    assert len(replaced["items"]) == 1 and replaced["items"][0].day == "Tuesday"
    assert setup_status(db, actor)["ready_for_validation"] is True
    semester_ids = [item.id for item in db.query(SemesterOffering).all()]
    assert validate_configuration(semester_ids, year.id, db, actor)["valid"] is True
