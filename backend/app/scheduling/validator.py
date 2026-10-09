from collections import Counter, defaultdict
from app.scheduling.domain import Assignment, Problem


def validate_schedule(problem: Problem, assignments: list[Assignment]) -> tuple[bool, list[dict], dict]:
    errors: list[dict] = []
    sessions = {s.id: s for s in problem.sessions}
    counts = Counter(a.session_id for a in assignments)
    for session in problem.sessions:
        if counts[session.id] != 1:
            errors.append({"code": "session_count", "session": session.id, "message": f"Expected one assignment, found {counts[session.id]}."})
    occupancy = {"room": defaultdict(list), "faculty": defaultdict(list), "group": defaultdict(list)}
    reservation_occupancy = {"room": set(), "faculty": set(), "group": set()}
    for r in problem.reservations:
        for p in r.periods:
            if r.room_id: reservation_occupancy["room"].add((r.room_id, r.day, p))
            if r.faculty_id: reservation_occupancy["faculty"].add((r.faculty_id, r.day, p))
            if r.group_id: reservation_occupancy["group"].add((r.group_id, r.day, p))
    faculty_daily = Counter()
    for a in assignments:
        s = sessions.get(a.session_id)
        if not s:
            errors.append({"code": "unknown_session", "session": a.session_id, "message": "Assignment references unknown session."})
            continue
        room = problem.rooms.get(a.room_id)
        periods = range(a.start_period, a.start_period + a.duration)
        if not room or room.capacity < s.enrollment or (s.kind == "lab" and room.kind != "lab") or not s.required_features.issubset(room.features):
            errors.append({"code": "ineligible_room", "session": a.session_id, "message": "Room does not satisfy type, capacity, or equipment requirements."})
        if any(p not in problem.periods or (a.day, p) in problem.blocked_slots for p in periods):
            errors.append({"code": "invalid_period", "session": a.session_id, "message": "Session is outside valid periods or crosses a blocked slot."})
        if s.fixed_day and (a.day != s.fixed_day or a.start_period != s.fixed_period):
            errors.append({"code": "fixed_session_moved", "session": a.session_id, "message": "Fixed session was not preserved."})
        for p in periods:
            occupancy["room"][a.room_id, a.day, p].append(a.session_id)
            for f in a.faculty_ids:
                occupancy["faculty"][f, a.day, p].append(a.session_id)
                faculty_daily[f, a.day] += 1
                if (a.day, p) in problem.faculty[f].unavailable: errors.append({"code": "faculty_unavailable", "session": a.session_id, "message": f"Faculty {f} is unavailable."})
            for g in a.group_ids: occupancy["group"][g, a.day, p].append(a.session_id)
    for kind, resources in occupancy.items():
        for key, ids in resources.items():
            capacity = problem.rooms[key[0]].concurrent_capacity if kind == "room" else 1
            if len(ids) > capacity:
                errors.append({"code": f"{kind}_collision", "resource": key[0], "day": key[1], "period": key[2], "sessions": ids, "message": f"{kind.title()} is double-booked."})
            if key in reservation_occupancy[kind]:
                errors.append({"code": "reservation_conflict", "resource_type": kind, "resource": key[0], "day": key[1], "period": key[2], "message": "Assignment conflicts with a fixed reservation."})
    for (f, day), load in faculty_daily.items():
        if load > problem.faculty[f].daily_limit: errors.append({"code": "faculty_daily_limit", "faculty_id": f, "day": day, "message": "Faculty daily workload limit exceeded."})
    metrics = calculate_metrics(problem, assignments)
    return not errors, errors, metrics


def calculate_metrics(problem: Problem, assignments: list[Assignment]) -> dict:
    by_group_day, by_faculty_day = defaultdict(set), defaultdict(set)
    used_room_periods = 0
    for a in assignments:
        for p in range(a.start_period, a.start_period + a.duration):
            used_room_periods += 1
            for g in a.group_ids: by_group_day[g, a.day].add(p)
            for f in a.faculty_ids: by_faculty_day[f, a.day].add(p)
    def gaps(mapping):
        return sum(max(ps) - min(ps) + 1 - len(ps) for ps in mapping.values() if ps)
    available = len(problem.days) * (len(problem.periods) - len({p for _, p in problem.blocked_slots})) * max(1, len(problem.rooms))
    return {"student_gaps": gaps(by_group_day), "faculty_gaps": gaps(by_faculty_day), "room_utilization": round(used_room_periods / available, 4), "scheduled_sessions": len(assignments)}

