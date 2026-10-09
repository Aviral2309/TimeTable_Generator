from app.db.session import Base, SessionLocal, engine
from app.models.entities import AcademicYear, Department, Faculty, Institute, Room, TimeSlot


def seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(Institute).count():
            print("Database already seeded")
            return
        db.add(Institute(name="Shri G. S. Institute of Technology and Science (Demonstration)"))
        departments = [Department(code="EE", name="Electrical Engineering"), Department(code="ECE", name="Electronics Engineering"), Department(code="CSE", name="Computer Science")]
        db.add_all(departments); db.flush()
        year = AcademicYear(name="2026-27"); db.add(year)
        for i in range(1, 16):
            dep = departments[0] if i <= 11 else departments[1] if i <= 13 else departments[2]
            db.add(Faculty(faculty_code=f"F{i:02}", name=f"Demo Faculty {i}", email=f"faculty{i}@example.edu", home_department_id=dep.id, weekly_limit=18, daily_limit=6))
        room_specs = [("EE-201", 70, "theory", ["projector"]), ("EE-205", 70, "theory", ["projector"]), ("EE-301", 70, "theory", ["projector"]), ("PES-LAB", 20, "lab", ["power-benches"]), ("MACH-LAB", 20, "lab", ["machines"]), ("ECE-102", 45, "theory", ["projector"]), ("EE-104", 25, "theory", ["projector"])]
        for code, capacity, kind, features in room_specs:
            db.add(Room(code=code, name=code, department_id=departments[0].id, capacity=capacity, room_type=kind, features=features))
        times = [("10:00", "11:00"), ("11:00", "12:00"), ("12:00", "13:00"), ("13:00", "14:00"), ("14:00", "15:00"), ("15:00", "16:00"), ("16:00", "17:00"), ("17:00", "18:00")]
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            for index, (start, end) in enumerate(times): db.add(TimeSlot(day=day, period_index=index, start_time=start, end_time=end, blocked=index == 3))
        db.commit(); print("Seeded demonstration master data")
    finally:
        db.close()


if __name__ == "__main__": seed()

