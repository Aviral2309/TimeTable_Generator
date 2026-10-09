from app.db.session import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.entities import AcademicYear, CourseOffering, Department, Faculty, FixedReservation, Institute, Room, SemesterOffering, TimeSlot, User


def seed_semester_configuration(db):
    if db.query(SemesterOffering).count(): return
    year = db.query(AcademicYear).filter_by(active=True).first(); department = db.query(Department).filter_by(code="EE").first()
    rooms = {r.code: r for r in db.query(Room).all()}; faculty = db.query(Faculty).order_by(Faculty.id).all()
    if not year or not department or len(faculty) < 12: return
    semester_rows = {}
    for number, strength, home in [(3, 60, "EE-201"), (5, 60, "EE-205"), (7, 60, "EE-301")]:
        item = SemesterOffering(academic_year_id=year.id, department_id=department.id, semester_number=number, section="ALL", strength=strength, home_room_id=rooms[home].id, home_room_policy="hard")
        db.add(item); db.flush(); semester_rows[number] = item
    def course(semester, code, name, weekly, teacher, room_codes, kind="theory", duration=1, enrollment=60, group=None, elective=None):
        db.add(CourseOffering(semester_offering_id=semester_rows[semester].id, code=code, name=name, kind=kind, sessions_per_week=weekly, duration_periods=duration, enrollment=enrollment, faculty_ids=[faculty[teacher-1].id], participant_group_ids=[group or f"SEM-{semester}"], eligible_room_ids=[rooms[x].id for x in room_codes], required_features=["power-benches"] if code.startswith("EE504") else [], elective_group=elective, parallel_elective=bool(elective)))
    course(3,"EE301","Electrical Machines I",3,1,["EE-201"]); course(3,"EE302","Network Analysis",3,2,["EE-201"]); course(3,"EE303","Analog Electronics",2,3,["EE-201"])
    course(5,"EE501","Power Systems I",3,1,["EE-205"]); course(5,"EE502","Control Systems",3,4,["EE-205"]); course(5,"EE503","Power Electronics",2,5,["EE-205"])
    for batch in range(1,5): course(5,f"EE504-B{batch}",f"Power Electronics Laboratory · Batch {batch}",1,9,["PES-LAB"],"lab",2,15,f"SEM-5-B{batch}")
    course(7,"EE701","Power System Protection",3,6,["EE-301"]); course(7,"EE702","High Voltage Engineering",3,7,["EE-301"]); course(7,"EE703","Industrial Drives",2,8,["EE-301"])
    course(7,"EEEL-MP","Microprocessors",1,10,["EE-104"],"elective",1,20,"SEM-7-MP","SEM-7-ELECTIVE")
    course(7,"EEEL-PS","Advanced Power Systems",1,11,["ECE-102"],"elective",1,40,"SEM-7-PS","SEM-7-ELECTIVE")
    course(3,"ECE-EE","Electronics for Electrical Engineers",1,12,["EE-201"],"theory",1,60,"SEM-3")
    if not db.query(FixedReservation).count():
        db.add(FixedReservation(academic_year_id=year.id, day="Monday", start_period=0, duration_periods=2, room_id=rooms["PES-LAB"].id, description="Existing first-year laboratory reservation"))
    db.commit()


def seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(Institute).count():
            if not db.query(User).count():
                faculty = db.query(Faculty).order_by(Faculty.id).all()
                demo_hash = hash_password("Demo@123")
                db.add_all([
                    User(email="admin@example.edu", name="Demo Administrator", password_hash=demo_hash, role="admin"),
                    User(email="faculty@example.edu", name="Demo Faculty", password_hash=demo_hash, role="faculty", faculty_id=faculty[0].id if faculty else None),
                    User(email="student@example.edu", name="Demo Student", password_hash=demo_hash, role="student", student_group_id="S5A"),
                ])
                db.commit(); print("Added Phase 2 demonstration accounts")
            else:
                print("Database already seeded")
            seed_semester_configuration(db)
            return
        db.add(Institute(name="Shri G. S. Institute of Technology and Science (Demonstration)"))
        departments = [Department(code="EE", name="Electrical Engineering"), Department(code="ECE", name="Electronics Engineering"), Department(code="CSE", name="Computer Science")]
        db.add_all(departments); db.flush()
        year = AcademicYear(name="2026-27"); db.add(year)
        faculty = []
        for i in range(1, 16):
            dep = departments[0] if i <= 11 else departments[1] if i <= 13 else departments[2]
            member = Faculty(faculty_code=f"F{i:02}", name=f"Demo Faculty {i}", email=f"faculty{i}@example.edu", home_department_id=dep.id, weekly_limit=18, daily_limit=6)
            db.add(member); faculty.append(member)
        db.flush()
        demo_hash = hash_password("Demo@123")
        db.add_all([
            User(email="admin@example.edu", name="Demo Administrator", password_hash=demo_hash, role="admin"),
            User(email="faculty@example.edu", name="Demo Faculty", password_hash=demo_hash, role="faculty", faculty_id=faculty[0].id),
            User(email="student@example.edu", name="Demo Student", password_hash=demo_hash, role="student", student_group_id="S5A"),
        ])
        room_specs = [("EE-201", 70, "theory", ["projector"]), ("EE-205", 70, "theory", ["projector"]), ("EE-301", 70, "theory", ["projector"]), ("PES-LAB", 20, "lab", ["power-benches"]), ("MACH-LAB", 20, "lab", ["machines"]), ("ECE-102", 45, "theory", ["projector"]), ("EE-104", 25, "theory", ["projector"])]
        for code, capacity, kind, features in room_specs:
            db.add(Room(code=code, name=code, department_id=departments[0].id, capacity=capacity, room_type=kind, features=features))
        times = [("10:00", "11:00"), ("11:00", "12:00"), ("12:00", "13:00"), ("13:00", "14:00"), ("14:00", "15:00"), ("15:00", "16:00"), ("16:00", "17:00"), ("17:00", "18:00")]
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            for index, (start, end) in enumerate(times): db.add(TimeSlot(day=day, period_index=index, start_time=start, end_time=end, blocked=index == 3))
        db.commit(); seed_semester_configuration(db); print("Seeded demonstration master data and semester configuration")
    finally:
        db.close()


if __name__ == "__main__": seed()

