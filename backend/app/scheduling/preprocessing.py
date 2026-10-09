from collections import Counter
from app.scheduling.domain import Problem, RequiredSession


def occupied_periods(problem: Problem, session: RequiredSession, day: str, start: int) -> tuple[int, ...] | None:
    periods = tuple(start + i for i in range(session.duration))
    if any(p not in problem.periods or (day, p) in problem.blocked_slots for p in periods):
        return None
    return periods


def candidates_for(problem: Problem, session: RequiredSession):
    room_ids = (session.fixed_room_id,) if session.fixed_room_id else session.eligible_room_ids
    days = [session.fixed_day] if session.fixed_day else problem.days
    starts = [session.fixed_period] if session.fixed_period is not None else problem.periods
    for room_id in room_ids:
        room = problem.rooms.get(room_id)
        if not room or room.capacity < session.enrollment or room.kind != session.kind and session.kind == "lab":
            continue
        if not session.required_features.issubset(room.features):
            continue
        for day in days:
            for start in starts:
                if session.kind == "lab":
                    first_start = min(problem.periods)
                    final_start = max(problem.periods) - session.duration + 1
                    boundary_starts = {first_start}
                    final_periods = tuple(final_start + i for i in range(session.duration))
                    if all(p in problem.periods and (day, p) not in problem.blocked_slots for p in final_periods):
                        boundary_starts.add(final_start)
                    if start not in boundary_starts:
                        continue
                periods = occupied_periods(problem, session, day, start)
                if periods is None or any((day, p) in room.unavailable for p in periods):
                    continue
                if any(any((day, p) in problem.faculty[f].unavailable for p in periods) for f in session.faculty_ids):
                    continue
                yield room_id, day, start, periods


def validate_problem(problem: Problem) -> list[dict]:
    errors: list[dict] = []
    faculty_load = Counter()
    for session in problem.sessions:
        if session.kind == "lab" and session.duration != 2:
            errors.append({"code": "invalid_lab_duration", "session": session.id, "message": f"{session.code} must be exactly two consecutive periods."})
            continue
        for faculty_id in session.faculty_ids:
            if faculty_id not in problem.faculty:
                errors.append({"code": "missing_faculty", "session": session.id, "message": f"{session.code} references missing faculty {faculty_id}."})
            else:
                faculty_load[faculty_id] += session.duration
        if not session.faculty_ids:
            errors.append({"code": "missing_faculty", "session": session.id, "message": f"{session.code} has no faculty assignment."})
        if session.enrollment <= 0:
            errors.append({"code": "invalid_enrollment", "session": session.id, "message": f"{session.code} enrollment must be positive."})
        choices = list(candidates_for(problem, session)) if all(f in problem.faculty for f in session.faculty_ids) else []
        if not choices:
            reason = "no room has sufficient capacity/features and a valid consecutive availability window"
            errors.append({"code": "no_candidate", "session": session.id, "message": f"{session.code} has {reason}."})
    for faculty_id, load in faculty_load.items():
        if faculty_id in problem.faculty and load > problem.faculty[faculty_id].weekly_limit:
            errors.append({"code": "faculty_weekly_overload", "faculty_id": faculty_id, "message": f"Faculty {problem.faculty[faculty_id].code} requires {load} periods but weekly limit is {problem.faculty[faculty_id].weekly_limit}."})
    return errors

