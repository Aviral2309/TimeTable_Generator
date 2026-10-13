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
    faculty_weekly = Counter()
    offering_days = Counter()
    cohort_full = set()
    cohort_subgroup = set()
    cohort_elective = set()
    for a in assignments:
        s = sessions.get(a.session_id)
        if not s:
            errors.append({"code": "unknown_session", "session": a.session_id, "message": "Assignment references unknown session."})
            continue
        room = problem.rooms.get(a.room_id)
        effective_room_ids = (s.fixed_room_id,) if s.fixed_room_id else s.eligible_room_ids
        offering_days[a.offering_id, a.day] += 1
        periods = range(a.start_period, a.start_period + a.duration)
        if not room or a.room_id not in effective_room_ids or room.capacity < s.enrollment or (s.kind == "lab" and room.kind != "lab") or not s.required_features.issubset(room.features):
            errors.append({"code": "ineligible_room", "session": a.session_id, "message": "Room does not satisfy type, capacity, or equipment requirements."})
        if any(p not in problem.periods or (a.day, p) in problem.blocked_slots for p in periods):
            errors.append({"code": "invalid_period", "session": a.session_id, "message": "Session is outside valid periods or crosses a blocked slot."})
        if room and any((a.day, p) in room.unavailable for p in periods):
            errors.append({"code": "room_unavailable", "session": a.session_id, "room_id": a.room_id, "message": f"Room {room.code} is unavailable during this session."})
        if s.kind == "lab":
            final_start = max(problem.periods) - s.duration + 1
            final_periods = tuple(final_start + i for i in range(s.duration))
            allowed_starts = {min(problem.periods)}
            if all(p in problem.periods and (a.day, p) not in problem.blocked_slots for p in final_periods): allowed_starts.add(final_start)
            if s.duration != 2:
                errors.append({"code": "invalid_lab_duration", "session": a.session_id, "message": "Laboratory must occupy exactly two consecutive periods."})
            if a.start_period not in allowed_starts:
                errors.append({"code": "lab_not_at_boundary", "session": a.session_id, "message": "Laboratory must be at the start or end of the working day, never between theory classes."})
        if s.fixed_day and (a.day != s.fixed_day or a.start_period != s.fixed_period):
            errors.append({"code": "fixed_session_moved", "session": a.session_id, "message": "Fixed session was not preserved."})
        for p in periods:
            occupancy["room"][a.room_id, a.day, p].append(a.session_id)
            for f in a.faculty_ids:
                occupancy["faculty"][f, a.day, p].append(a.session_id)
                faculty_daily[f, a.day] += 1
                faculty_weekly[f] += 1
                if (a.day, p) in problem.faculty[f].unavailable: errors.append({"code": "faculty_unavailable", "session": a.session_id, "message": f"Faculty {f} is unavailable."})
            for g in a.group_ids: occupancy["group"][g, a.day, p].append(a.session_id)
            if s.cohort_id:
                target = cohort_elective if s.is_elective else cohort_subgroup if s.is_subgroup else cohort_full
                target.add((s.cohort_id, a.day, p))
    for kind, resources in occupancy.items():
        for key, ids in resources.items():
            capacity = problem.rooms[key[0]].concurrent_capacity if kind == "room" else 1
            if len(ids) > capacity:
                errors.append({"code": f"{kind}_collision", "resource": key[0], "day": key[1], "period": key[2], "sessions": ids, "message": f"{kind.title()} is double-booked."})
            if key in reservation_occupancy[kind]:
                errors.append({"code": "reservation_conflict", "resource_type": kind, "resource": key[0], "day": key[1], "period": key[2], "message": "Assignment conflicts with a fixed reservation."})
    for (f, day), load in faculty_daily.items():
        if load > problem.faculty[f].daily_limit: errors.append({"code": "faculty_daily_limit", "faculty_id": f, "day": day, "message": "Faculty daily workload limit exceeded."})
    for faculty_id, load in faculty_weekly.items():
        if load > problem.faculty[faculty_id].weekly_limit:
            errors.append({"code": "faculty_weekly_limit", "faculty_id": faculty_id, "message": "Faculty weekly workload limit exceeded."})
    for faculty_id, faculty in problem.faculty.items():
        for day in problem.days:
            occupied = sorted(period for (resource, occupied_day, period), ids in occupancy["faculty"].items() if resource == faculty_id and occupied_day == day and ids)
            longest = current = 0
            previous = None
            for period in occupied:
                current = current + 1 if previous is not None and period == previous + 1 else 1
                longest = max(longest, current)
                previous = period
            if longest > faculty.max_consecutive:
                errors.append({"code": "faculty_max_consecutive", "faculty_id": faculty_id, "day": day, "message": f"Faculty exceeds the maximum of {faculty.max_consecutive} consecutive periods."})
    for (offering_id, day), count in offering_days.items():
        if count > 1:
            errors.append({"code": "same_subject_repeated", "offering_id": offering_id, "day": day, "message": "The same subject cannot have more than one class on the same day."})
    for cohort_id, day, period in sorted(cohort_full & cohort_subgroup):
        errors.append({"code": "cohort_subgroup_conflict", "cohort": cohort_id, "day": day, "period": period, "message": "A full-semester class cannot overlap one of that semester's batch labs."})
    for cohort_id, day, period in sorted(cohort_full & cohort_elective):
        errors.append({"code": "cohort_elective_conflict", "cohort": cohort_id, "day": day, "period": period, "message": "A full-cohort class cannot overlap that cohort's elective block."})
    for cohort_id, day, period in sorted(cohort_subgroup & cohort_elective):
        errors.append({"code": "subgroup_elective_conflict", "cohort": cohort_id, "day": day, "period": period, "message": "A batch lab cannot overlap that semester's elective block."})
    assignment_by_session = {a.session_id: a for a in assignments}
    parallel_groups = defaultdict(list)
    for session in problem.sessions:
        if session.parallel_key: parallel_groups[session.parallel_key].append(session.id)
    for key, session_ids in parallel_groups.items():
        placements = {(assignment_by_session[sid].day, assignment_by_session[sid].start_period) for sid in session_ids if sid in assignment_by_session}
        if len(placements) > 1:
            errors.append({"code": "parallel_elective_mismatch", "parallel_group": key, "sessions": session_ids, "message": "All alternatives in a parallel elective group must start at the same time."})
    metrics = calculate_metrics(problem, assignments)
    return not errors, errors, metrics


def calculate_metrics(problem: Problem, assignments: list[Assignment]) -> dict:
    by_group_day, by_faculty_day = defaultdict(set), defaultdict(set)
    group_room_period = defaultdict(set)
    sessions = {session.id: session for session in problem.sessions}
    cohort_groups = defaultdict(set)
    cohort_subgroups = defaultdict(set)
    for session in problem.sessions:
        if session.cohort_id and (session.is_subgroup or session.is_elective):
            cohort_groups[session.cohort_id].update(session.group_ids)
        if session.cohort_id and session.is_subgroup:
            cohort_subgroups[session.cohort_id].update(session.group_ids)
    used_room_periods = 0
    for a in assignments:
        session = sessions.get(a.session_id)
        effective_groups = set(a.group_ids)
        if session and session.cohort_id and not session.is_subgroup and not session.is_elective:
            effective_groups.update(cohort_groups[session.cohort_id])
        elif session and session.cohort_id and session.is_elective:
            effective_groups.update(cohort_subgroups[session.cohort_id])
        for p in range(a.start_period, a.start_period + a.duration):
            used_room_periods += 1
            for g in effective_groups:
                by_group_day[g, a.day].add(p)
                group_room_period[g, a.day, p].add(a.room_id)
            for f in a.faculty_ids: by_faculty_day[f, a.day].add(p)
    def gaps(mapping):
        total = 0
        for (_, day), ps in mapping.items():
            if not ps: continue
            valid_between = {p for p in problem.periods if min(ps) <= p <= max(ps) and (day, p) not in problem.blocked_slots}
            total += len(valid_between - ps)
        return total
    available = len(problem.days) * (len(problem.periods) - len({p for _, p in problem.blocked_slots})) * max(1, len(problem.rooms))
    student_gaps = gaps(by_group_day)
    faculty_gaps = gaps(by_faculty_day)
    late_student_periods = sum(sum(p >= 6 for p in periods) for periods in by_group_day.values())
    isolated_student_days = sum(len(periods) == 1 for periods in by_group_day.values())
    room_changes = 0
    for (group, day), periods in by_group_day.items():
        ordered = sorted(periods)
        for previous, current in zip(ordered, ordered[1:]):
            if current != previous + 1: continue
            previous_rooms = group_room_period[group, day, previous]
            current_rooms = group_room_period[group, day, current]
            if len(previous_rooms) == 1 and len(current_rooms) == 1 and previous_rooms != current_rooms:
                room_changes += 1
    return {"student_gaps": student_gaps, "faculty_gaps": faculty_gaps, "late_student_periods": late_student_periods, "isolated_student_days": isolated_student_days, "student_room_changes": room_changes, "room_utilization": round(used_room_periods / available, 4), "scheduled_sessions": len(assignments)}

