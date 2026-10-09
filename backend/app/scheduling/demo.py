from app.scheduling.domain import FacultyResource, Problem, RequiredSession, ResourceReservation, RoomResource


def build_demo_problem() -> Problem:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods = list(range(8))
    rooms = {
        1: RoomResource(1, "EE-201", 70, "theory", frozenset({"projector"})),
        2: RoomResource(2, "EE-205", 70, "theory", frozenset({"projector"})),
        3: RoomResource(3, "EE-301", 70, "theory", frozenset({"projector"})),
        4: RoomResource(4, "PES-LAB", 20, "lab", frozenset({"power-benches"})),
        5: RoomResource(5, "MACH-LAB", 20, "lab", frozenset({"machines"})),
        6: RoomResource(6, "ECE-102", 45, "theory", frozenset({"projector"})),
        7: RoomResource(7, "EE-104", 25, "theory", frozenset({"projector"})),
    }
    faculty = {i: FacultyResource(i, f"F{i:02}", 18, 6, frozenset({("Wednesday", 1)}) if i == 4 else frozenset()) for i in range(1, 16)}
    sessions = []
    offering = 1
    semester_specs = [
        ("S3A", 60, [("EE301", 3, 1), ("EE302", 3, 2), ("EE303", 2, 3)]),
        ("S5A", 60, [("EE501", 3, 1), ("EE502", 3, 4), ("EE503", 2, 5)]),
        ("S7A", 60, [("EE701", 3, 6), ("EE702", 3, 7), ("EE703", 2, 8)]),
    ]
    home_rooms = {"S3A": (1,), "S5A": (2,), "S7A": (3,)}
    for group, strength, courses in semester_specs:
        for code, count, teacher in courses:
            for occurrence in range(count):
                sessions.append(RequiredSession(f"{code}-{occurrence+1}", offering, occurrence, code, "theory", 1, strength, (teacher,), (group,), home_rooms[group]))
            offering += 1
    for batch_no in range(1, 5):
        sessions.append(RequiredSession(f"EE504-B{batch_no}", offering, batch_no, "EE504", "lab", 2, 15, (9,), (f"S5B{batch_no}", "S5A"), (4,), frozenset({"power-benches"}), frozenset({0, 1, 2})))
    offering += 1
    sessions.extend([
        RequiredSession("ELEC-MP", offering, 0, "EE-EL-MP", "theory", 1, 20, (10,), ("S7-MP",), (7,), parallel_key="S7-ELECTIVE"),
        RequiredSession("ELEC-PS", offering + 1, 0, "EE-EL-PS", "theory", 1, 40, (11,), ("S7-PS",), (6,), parallel_key="S7-ELECTIVE"),
        RequiredSession("EXT-ECE", offering + 2, 0, "ECE-EE", "theory", 1, 60, (12,), ("S3A",), (1,), fixed_day="Thursday", fixed_period=2, fixed_room_id=1),
    ])
    reservations = [ResourceReservation("Monday", (0, 1), room_id=4, description="Existing first-year Power Electronics Lab")]
    return Problem(days, periods, {(d, 3) for d in days}, rooms, faculty, sessions, reservations, {"preference": 3, "late": 4, "same_day": 4, "student_gaps": 100, "faculty_gaps": 5, "late_student_periods": 12, "isolated_student_days": 10})

