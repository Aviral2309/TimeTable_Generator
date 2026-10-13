from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import bootstrap_admin, bootstrap_status
from app.api.master_data import faculty_availability, faculty_create, faculty_delete, faculty_update, replace_faculty_availability, replace_room_availability, reservation_create, reservation_delete, reservation_update, room_availability, room_create, room_delete, room_update
from app.api.setup import create_academic_year, create_course_offering, create_demo_data, create_department, create_institute, create_lab_batch_offerings, create_semester, create_term_cohorts, create_working_week, delete_course_offering, delete_semester, setup_status, update_course_offering, update_semester, validate_configuration
from app.db.session import Base
from app.models.entities import AcademicYear, CourseOffering, Faculty, FixedReservation, SemesterOffering, User
from app.schemas.auth import BootstrapAdminRequest
from app.schemas.master_data import FacultyAvailabilitySlot, FacultyCreate, ReservationCreate, RoomAvailabilitySlot, RoomCreate
from app.schemas.setup import AcademicYearCreate, CourseOfferingCreate, DemoDataCreate, DepartmentCreate, InstituteCreate, LabBatchAllocationCreate, LabOfferingBatchCreate, SemesterCreate, TermCohortsCreate, WorkingWeekCreate


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
    create_working_week(WorkingWeekCreate(days=["Monday", "Tuesday"], start_hour=9, periods_per_day=6, lunch_after_period=3), db, actor)

    configured = setup_status(db, actor)
    assert configured["counts"]["time_slots"] == 12
    assert configured["steps"][0]["complete"] is True
    assert configured["ready_for_validation"] is False


def test_admin_can_create_update_and_delete_operational_records():
    db = empty_database(); actor = User(email="admin@college.edu", name="Admin", password_hash="x", role="admin")
    create_institute(InstituteCreate(name="Example Institute"), db, actor)
    department = create_department(DepartmentCreate(code="EE", name="Electrical Engineering"), db, actor)
    year = create_academic_year(AcademicYearCreate(name="2026-27"), db, actor)
    create_working_week(WorkingWeekCreate(days=["Monday", "Tuesday"], start_hour=9, periods_per_day=6, lunch_after_period=3), db, actor)
    faculty_body = FacultyCreate(faculty_code="F01", name="Teacher One", email="one@sgsits.ac.in", home_department_id=department.id)
    faculty = faculty_create(faculty_body, db, actor)
    faculty = faculty_update(faculty.id, faculty_body.model_copy(update={"name": "Teacher Updated"}), db, actor)
    assert faculty.name == "Teacher Updated"
    room_body = RoomCreate(code="R1", name="Room One", department_id=department.id, capacity=70, room_type="theory", features=["projector"])
    room = room_create(room_body, db, actor)
    room = room_update(room.id, room_body.model_copy(update={"name": "Room Updated"}), db, actor)
    assert room.name == "Room Updated"
    room_constraints = replace_room_availability(room.id, [RoomAvailabilitySlot(day="Monday", period_index=2, available=False, note="Used by Civil Engineering")], db, actor)
    assert room_constraints["items"][0].note == "Used by Civil Engineering"
    assert room_availability(room.id, db, actor)["items"][0].available is False
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
    replaced = replace_faculty_availability(external_teacher.id, [FacultyAvailabilitySlot(day="Tuesday", period_index=2, available=False, note="Other-department lecture")], db, actor)
    assert len(replaced["items"]) == 1 and replaced["items"][0].day == "Tuesday" and replaced["items"][0].note == "Other-department lecture"
    assert setup_status(db, actor)["ready_for_validation"] is True
    semester_ids = [item.id for item in db.query(SemesterOffering).all()]
    assert validate_configuration(semester_ids, year.id, db, actor)["valid"] is True


def test_term_selection_creates_only_the_expected_semesters():
    db = empty_database(); actor = User(email="admin@college.edu", name="Admin", password_hash="x", role="admin")
    department = create_department(DepartmentCreate(code="EE", name="Electrical Engineering"), db, actor)
    year = create_academic_year(AcademicYearCreate(name="2027 Even", term_type="even"), db, actor)
    result = create_term_cohorts(TermCohortsCreate(academic_year_id=year.id, department_id=department.id, default_strength=72), db, actor)
    assert {item.semester_number for item in result["items"]} == {2, 4, 6}
    assert all(item.home_room_id is None and item.strength == 72 for item in result["items"])


def test_capability_names_allow_spaces_and_remove_case_insensitive_duplicates():
    room = RoomCreate(code="NL", name="Network and Machines Lab", capacity=40, room_type="lab", features=[" Network   Lab ", "network lab", "Electrical Machines"])
    assert room.features == ["Network Lab", "Electrical Machines"]
    subject = CourseOfferingCreate(semester_offering_id=1, code="EE-LAB", name="Network Lab", kind="lab", sessions_per_week=1, duration_periods=2, enrollment=20, faculty_ids=[1], eligible_room_ids=[], required_features=[" network   LAB "])
    assert subject.required_features == ["network LAB"]


def test_admin_creates_every_regular_lab_batch_in_one_atomic_request():
    db = empty_database(); actor = User(email="admin@college.edu", name="Admin", password_hash="x", role="admin")
    department = create_department(DepartmentCreate(code="EE", name="Electrical Engineering"), db, actor)
    year = create_academic_year(AcademicYearCreate(name="2026-27 Odd", term_type="odd"), db, actor)
    faculty = faculty_create(FacultyCreate(faculty_code="F01", name="Teacher One", email="one@sgsits.ac.in", home_department_id=department.id), db, actor)
    lab = room_create(RoomCreate(code="NL", name="Network Lab", department_id=department.id, capacity=20, room_type="lab", features=["Network Lab"]), db, actor)
    semester = create_semester(SemesterCreate(academic_year_id=year.id, department_id=department.id, semester_number=3, strength=61), db, actor)
    body = LabOfferingBatchCreate(
        semester_offering_id=semester.id,
        code="EE3401",
        name="Network Laboratory",
        sessions_per_week=1,
        total_enrollment=61,
        required_features=["Network Lab"],
        batches=[LabBatchAllocationCreate(participant_group=f"B{index}", faculty_ids=[faculty.id], room_id=lab.id) for index in range(1, 5)],
    )

    result = create_lab_batch_offerings(body, db, actor)

    assert result["batch_count"] == 4
    assert [item.participant_group_ids for item in result["items"]] == [["SEM-3-B1"], ["SEM-3-B2"], ["SEM-3-B3"], ["SEM-3-B4"]]
    assert [item.enrollment for item in result["items"]] == [16, 15, 15, 15]
    assert all(item.fixed_room_id == lab.id and item.duration_periods == 2 for item in result["items"])


def test_parallel_electives_get_distinct_student_groups_automatically():
    db = empty_database(); actor = User(email="admin@college.edu", name="Admin", password_hash="x", role="admin")
    department = create_department(DepartmentCreate(code="EE", name="Electrical Engineering"), db, actor)
    year = create_academic_year(AcademicYearCreate(name="2026-27 Odd", term_type="odd"), db, actor)
    faculty = faculty_create(FacultyCreate(faculty_code="F01", name="Teacher One", email="one@sgsits.ac.in", home_department_id=department.id), db, actor)
    room = room_create(RoomCreate(code="R1", name="Room One", department_id=department.id, capacity=80, room_type="theory"), db, actor)
    semester = create_semester(SemesterCreate(academic_year_id=year.id, department_id=department.id, semester_number=7, strength=60), db, actor)
    common = dict(
        semester_offering_id=semester.id,
        kind="elective",
        sessions_per_week=2,
        duration_periods=1,
        enrollment=30,
        faculty_ids=[faculty.id],
        eligible_room_ids=[room.id],
        elective_group="SEM-7-ELECTIVE",
        parallel_elective=True,
    )

    first = create_course_offering(CourseOfferingCreate(code="EL-A", name="Elective A", **common), db, actor)
    second = create_course_offering(CourseOfferingCreate(code="EL-B", name="Elective B", **common), db, actor)

    assert first.participant_group_ids == ["SEM-7-ELECTIVE-EL-A"]
    assert second.participant_group_ids == ["SEM-7-ELECTIVE-EL-B"]
    assert first.participant_group_ids != second.participant_group_ids
