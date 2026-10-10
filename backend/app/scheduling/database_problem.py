from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import CourseOffering, Faculty, FacultyAvailability, FixedReservation, Room, SemesterOffering, TimeSlot
from app.scheduling.domain import FacultyResource, Problem, RequiredSession, ResourceReservation, RoomResource


def normalized_capabilities(values: list[str] | None) -> frozenset[str]:
    return frozenset(" ".join(value.strip().split()).casefold() for value in (values or []) if value.strip())


def build_database_problem(db: Session, academic_year_id: int, semester_ids: list[int]) -> Problem:
    semesters = db.scalars(select(SemesterOffering).where(SemesterOffering.id.in_(semester_ids), SemesterOffering.academic_year_id == academic_year_id)).all()
    if len(semesters) != len(set(semester_ids)):
        raise ValueError("One or more selected semesters do not belong to the academic year")
    slots = db.scalars(select(TimeSlot).order_by(TimeSlot.period_index)).all()
    if not slots: raise ValueError("No institutional time slots are configured")
    days = list(dict.fromkeys(s.day for s in slots))
    periods = sorted({s.period_index for s in slots})
    blocked = {(s.day, s.period_index) for s in slots if s.blocked}
    db_rooms = db.scalars(select(Room).where(Room.active.is_(True))).all()
    rooms = {r.id: RoomResource(r.id, r.code, r.capacity, r.room_type, normalized_capabilities(r.features), r.concurrent_capacity) for r in db_rooms}
    availability = db.scalars(select(FacultyAvailability)).all()
    unavailable: dict[int, set[tuple[str, int]]] = {}
    preferences: dict[int, dict[tuple[str, int], int]] = {}
    for a in availability:
        if not a.available: unavailable.setdefault(a.faculty_id, set()).add((a.day, a.period_index))
        if a.preference: preferences.setdefault(a.faculty_id, {})[(a.day, a.period_index)] = a.preference
    db_faculty = db.scalars(select(Faculty).where(Faculty.active.is_(True))).all()
    faculty = {f.id: FacultyResource(f.id, f.faculty_code, f.weekly_limit, f.daily_limit, frozenset(unavailable.get(f.id, set())), preferences.get(f.id, {})) for f in db_faculty}
    semester_map = {s.id: s for s in semesters}
    offerings = db.scalars(select(CourseOffering).where(CourseOffering.semester_offering_id.in_(semester_ids))).all()
    sessions: list[RequiredSession] = []
    for offering in offerings:
        semester = semester_map[offering.semester_offering_id]
        cohort = f"SEM-{semester.semester_number}"
        groups = tuple(offering.participant_group_ids or [cohort])
        is_subgroup = cohort not in groups and offering.kind != "elective"
        if offering.eligible_room_ids:
            eligible = tuple(offering.eligible_room_ids)
        elif offering.kind == "lab":
            eligible = tuple(room.id for room in db_rooms if room.room_type == "lab")
        else:
            eligible = tuple(room.id for room in db_rooms if room.room_type == "theory")
        if offering.kind == "theory" and semester.home_room_policy == "hard" and semester.home_room_id:
            eligible = (semester.home_room_id,)
        preferred = frozenset({0, 1, 2}) if offering.kind == "lab" and semester.semester_number == 3 else frozenset({4, 5, 6}) if offering.kind == "lab" and semester.semester_number == 5 else frozenset()
        for occurrence in range(offering.sessions_per_week):
            parallel_key = f"{offering.elective_group}-{occurrence}" if offering.parallel_elective else None
            sessions.append(RequiredSession(f"offering-{offering.id}-{occurrence+1}", offering.id, occurrence, offering.code, "lab" if offering.kind == "lab" else "theory", offering.duration_periods, offering.enrollment, tuple(offering.faculty_ids), groups, eligible, normalized_capabilities(offering.required_features), preferred, offering.fixed_day, offering.fixed_period, offering.fixed_room_id, parallel_key, cohort, offering.kind == "elective", is_subgroup))
    reservations = [ResourceReservation(r.day, tuple(range(r.start_period, r.start_period + r.duration_periods)), r.room_id, r.faculty_id, r.participant_group_id, r.description) for r in db.scalars(select(FixedReservation).where(FixedReservation.academic_year_id == academic_year_id)).all()]
    return Problem(days, periods, blocked, rooms, faculty, sessions, reservations, {"preference": 12, "late": 4, "same_day": 8, "student_gaps": 100, "faculty_gaps": 5, "late_student_periods": 12, "isolated_student_days": 10})

