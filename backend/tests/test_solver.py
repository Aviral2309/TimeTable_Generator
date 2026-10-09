from dataclasses import replace
from app.scheduling.annealing import refine, soft_cost
from app.scheduling.demo import build_demo_problem
from app.scheduling.domain import Assignment, FacultyResource, Problem, RequiredSession, ResourceReservation, RoomResource
from app.scheduling.solver import solve
from app.scheduling.validator import validate_schedule


def solved_demo():
    problem = build_demo_problem()
    result = solve(problem, 15, 7)
    assert result.status in {"optimal", "feasible"}, result.diagnostics
    valid, errors, metrics = validate_schedule(problem, result.assignments)
    assert valid, errors
    return problem, result, metrics


def test_three_semesters_generate_and_validate():
    problem, result, metrics = solved_demo()
    assert len(result.assignments) == len(problem.sessions)
    assert metrics["scheduled_sessions"] == len(problem.sessions)


def test_shared_faculty_and_rooms_never_collide():
    problem, result, _ = solved_demo()
    occupied = set()
    for a in result.assignments:
        for p in range(a.start_period, a.start_period + a.duration):
            for f in a.faculty_ids:
                assert ("f", f, a.day, p) not in occupied
                occupied.add(("f", f, a.day, p))
            assert ("r", a.room_id, a.day, p) not in occupied
            occupied.add(("r", a.room_id, a.day, p))


def test_first_year_reservation_and_two_hour_labs_and_lunch():
    problem, result, _ = solved_demo()
    labs = [a for a in result.assignments if a.session_id.startswith("EE504")]
    assert len(labs) == 4
    assert all(a.duration == 2 and a.start_period != 2 for a in labs)
    assert all(not (a.room_id == 4 and a.day == "Monday" and a.start_period in {0, 1}) for a in labs)


def test_parallel_electives_and_enrollment_sized_rooms():
    problem, result, _ = solved_demo()
    elective = {a.session_id: a for a in result.assignments if a.session_id.startswith("ELEC")}
    assert (elective["ELEC-MP"].day, elective["ELEC-MP"].start_period) == (elective["ELEC-PS"].day, elective["ELEC-PS"].start_period)
    assert problem.rooms[elective["ELEC-MP"].room_id].capacity >= 20
    assert problem.rooms[elective["ELEC-PS"].room_id].capacity >= 40


def test_home_rooms_and_fixed_external_lecture():
    _, result, _ = solved_demo()
    expected = {"EE30": 1, "EE50": 2, "EE70": 3}
    for a in result.assignments:
        for prefix, room in expected.items():
            if a.session_id.startswith(prefix) and not a.session_id.startswith("EE504"):
                assert a.room_id == room
    fixed = next(a for a in result.assignments if a.session_id == "EXT-ECE")
    assert (fixed.day, fixed.start_period, fixed.room_id) == ("Thursday", 2, 1)


def tiny_problem(session, room=None, faculty=None, reservations=None):
    room = room or RoomResource(1, "R1", 60, "theory")
    faculty = faculty or FacultyResource(1, "F1")
    return Problem(["Monday"], [0, 1, 2, 3], {("Monday", 2)}, {room.id: room}, {faculty.id: faculty}, [session], reservations or [])


def test_capacity_too_small_has_actionable_diagnostic():
    p = tiny_problem(RequiredSession("s", 1, 0, "BIG", "theory", 1, 70, (1,), ("g",), (1,)))
    result = solve(p)
    assert result.status == "invalid_input"
    assert result.diagnostics[0]["code"] == "no_candidate"


def test_faculty_unavailable_and_impossible_workload():
    f = FacultyResource(1, "F1", weekly_limit=0, unavailable=frozenset({("Monday", 0), ("Monday", 1), ("Monday", 3)}))
    p = tiny_problem(RequiredSession("s", 1, 0, "C", "theory", 1, 20, (1,), ("g",), (1,)), faculty=f)
    result = solve(p)
    assert result.status == "invalid_input"
    assert {d["code"] for d in result.diagnostics} >= {"no_candidate", "faculty_weekly_overload"}


def test_lab_has_no_consecutive_window():
    room = RoomResource(1, "L1", 30, "lab", frozenset({"kit"}))
    session = RequiredSession("lab", 1, 0, "LAB", "lab", 2, 20, (1,), ("g",), (1,), frozenset({"kit"}))
    p = tiny_problem(session, room)
    p.blocked_slots = {("Monday", 1), ("Monday", 3)}
    result = solve(p)
    assert result.status == "invalid_input"


def test_reservation_removes_last_candidate():
    s = RequiredSession("s", 1, 0, "C", "theory", 1, 20, (1,), ("g",), (1,), fixed_day="Monday", fixed_period=0)
    p = tiny_problem(s, reservations=[ResourceReservation("Monday", (0,), room_id=1)])
    result = solve(p)
    assert result.status == "invalid_input"
    assert result.diagnostics[-1]["code"] == "reservation_conflict"


def test_validator_catches_injected_collision():
    problem, result, _ = solved_demo()
    a, b = result.assignments[:2]
    damaged = list(result.assignments)
    damaged[1] = replace(b, day=a.day, start_period=a.start_period, room_id=a.room_id, faculty_ids=a.faculty_ids)
    valid, errors, _ = validate_schedule(problem, damaged)
    assert not valid
    assert any(e["code"] in {"room_collision", "faculty_collision"} for e in errors)


def test_annealing_preserves_feasibility_and_best_cost():
    problem, result, _ = solved_demo()
    improved, stats = refine(problem, result.assignments, 80, 9)
    valid, errors, _ = validate_schedule(problem, improved)
    assert valid, errors
    assert soft_cost(problem, improved) <= soft_cost(problem, result.assignments)
    assert stats["best_cost"] <= stats["initial_cost"]

