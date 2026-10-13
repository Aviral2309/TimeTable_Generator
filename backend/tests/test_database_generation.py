from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.session import Base
from app.models.entities import AcademicYear, CourseOffering, Department, Faculty, Room, RoomAvailability, SemesterOffering, TimeSlot
from app.scheduling.database_problem import build_database_problem
from app.scheduling.solver import solve
from app.scheduling.validator import validate_schedule


def configured_problem():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine); db = sessionmaker(bind=engine, expire_on_commit=False)()
    year=AcademicYear(name="2027-28"); dep=Department(code="EE",name="Electrical"); db.add_all([year,dep]); db.flush()
    rooms=[]
    for i in range(3): rooms.append(Room(code=f"R{i+1}",name=f"Room {i+1}",department_id=dep.id,capacity=70,room_type="theory",features=[]))
    lab=Room(code="LAB",name="Lab",department_id=dep.id,capacity=20,room_type="lab",features=["kit"]); db.add_all(rooms+[lab])
    teachers=[Faculty(faculty_code=f"F{i}",name=f"Faculty {i}",email=f"f{i}@test.edu",home_department_id=dep.id,weekly_limit=18,daily_limit=6) for i in range(1,5)]; db.add_all(teachers); db.flush()
    semesters=[]
    for index, number in enumerate([3,5,7]):
        sem=SemesterOffering(academic_year_id=year.id,department_id=dep.id,semester_number=number,section="ALL",strength=60,home_room_id=rooms[index].id,home_room_policy="hard");db.add(sem);db.flush();semesters.append(sem)
        db.add(CourseOffering(semester_offering_id=sem.id,code=f"EE{number}01",name="Theory",kind="theory",sessions_per_week=2,duration_periods=1,enrollment=60,faculty_ids=[teachers[index].id],participant_group_ids=[f"SEM-{number}"],eligible_room_ids=[rooms[index].id],required_features=[]))
    db.add(CourseOffering(semester_offering_id=semesters[1].id,code="EE-LAB",name="Lab",kind="lab",sessions_per_week=1,duration_periods=2,enrollment=20,faculty_ids=[teachers[3].id],participant_group_ids=["SEM-5-B1"],eligible_room_ids=[lab.id],required_features=["kit"]))
    db.add(CourseOffering(semester_offering_id=semesters[2].id,code="EL-A",name="Elective A",kind="elective",sessions_per_week=1,duration_periods=1,enrollment=30,faculty_ids=[teachers[0].id],participant_group_ids=["SEM-7-A"],eligible_room_ids=[rooms[0].id],required_features=[],elective_group="SEM-7-EL",parallel_elective=True))
    db.add(CourseOffering(semester_offering_id=semesters[2].id,code="EL-B",name="Elective B",kind="elective",sessions_per_week=1,duration_periods=1,enrollment=30,faculty_ids=[teachers[1].id],participant_group_ids=["SEM-7-B"],eligible_room_ids=[rooms[1].id],required_features=[],elective_group="SEM-7-EL",parallel_elective=True))
    times=[("10:00","11:00"),("11:00","12:00"),("12:00","13:00"),("13:00","14:00"),("14:00","15:00")]
    for day in ["Monday","Tuesday","Wednesday"]:
        for i,(start,end) in enumerate(times): db.add(TimeSlot(day=day,period_index=i,start_time=start,end_time=end,blocked=i==3))
    db.commit(); return db,year,[s.id for s in semesters]


def test_database_records_drive_exactly_three_cohort_schedule():
    db,year,ids=configured_problem(); problem=build_database_problem(db,year.id,ids)
    assert {g for s in problem.sessions for g in s.group_ids if g.startswith("SEM-")} >= {"SEM-3","SEM-5","SEM-7"}
    result=solve(problem,10,42); valid,errors,metrics=validate_schedule(problem,result.assignments)
    assert result.status in {"optimal","feasible"}; assert valid,errors; assert metrics["scheduled_sessions"]==9
    assert all("section" not in g.lower() for s in problem.sessions for g in s.group_ids)


def test_lab_from_database_is_consecutive_and_cannot_cross_lunch():
    db,year,ids=configured_problem(); problem=build_database_problem(db,year.id,ids); result=solve(problem,10,42)
    lab=next(x for x in result.assignments if x.session_id.startswith("offering-4"))
    assert lab.duration==2 and lab.start_period == 0


def test_electives_are_parallel_and_do_not_overlap_full_cohort_class():
    db,year,ids=configured_problem(); problem=build_database_problem(db,year.id,ids); result=solve(problem,10,42)
    electives=[a for a in result.assignments if a.offering_id in {5,6}]
    assert len({(a.day,a.start_period) for a in electives})==1
    elective_slots={(electives[0].day,electives[0].start_period)}
    semester_seven_regular=[a for a in result.assignments if a.offering_id==3]
    assert not elective_slots & {(a.day,a.start_period) for a in semester_seven_regular}


def test_room_unavailability_is_a_hard_generation_constraint():
    db, year, ids = configured_problem()
    room = db.scalar(select(Room).where(Room.code == "R1"))
    db.add_all([
        RoomAvailability(room_id=room.id, day="Monday", period_index=0, available=False, note="Used by another department"),
        RoomAvailability(room_id=room.id, day="Monday", period_index=1, available=False, note="Used by another department"),
    ])
    db.commit()

    problem = build_database_problem(db, year.id, ids)
    result = solve(problem, 10, 42)
    valid, errors, _ = validate_schedule(problem, result.assignments)

    assert valid, errors
    assert not any(a.room_id == room.id and a.day == "Monday" and a.start_period in {0, 1} for a in result.assignments)

