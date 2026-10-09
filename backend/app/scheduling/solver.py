from __future__ import annotations
from collections import defaultdict
from time import perf_counter
from ortools.sat.python import cp_model
from app.scheduling.domain import Assignment, Problem, SolveResult
from app.scheduling.preprocessing import candidates_for, validate_problem


STATUS = {
    cp_model.OPTIMAL: "optimal", cp_model.FEASIBLE: "feasible",
    cp_model.INFEASIBLE: "infeasible", cp_model.MODEL_INVALID: "model_invalid",
    cp_model.UNKNOWN: "unknown",
}


def solve(problem: Problem, time_limit: float = 30, random_seed: int = 42) -> SolveResult:
    started = perf_counter()
    diagnostics = validate_problem(problem)
    if diagnostics:
        return SolveResult("invalid_input", [], None, perf_counter() - started, diagnostics)
    model = cp_model.CpModel()
    variables = {}
    candidate_map = {}
    by_room_slot, by_faculty_slot, by_group_slot = defaultdict(list), defaultdict(list), defaultdict(list)
    by_faculty_day = defaultdict(list)
    by_offering_day = defaultdict(list)
    start_by_session_day = defaultdict(list)
    penalties = []
    reservation_rooms = {(r.room_id, r.day, p) for r in problem.reservations for p in r.periods if r.room_id}
    reservation_faculty = {(r.faculty_id, r.day, p) for r in problem.reservations for p in r.periods if r.faculty_id}
    reservation_groups = {(r.group_id, r.day, p) for r in problem.reservations for p in r.periods if r.group_id}
    for session in problem.sessions:
        for idx, (room_id, day, start, periods) in enumerate(candidates_for(problem, session)):
            if any((room_id, day, p) in reservation_rooms for p in periods):
                continue
            if any((f, day, p) in reservation_faculty for f in session.faculty_ids for p in periods):
                continue
            if any((g, day, p) in reservation_groups for g in session.group_ids for p in periods):
                continue
            key = (session.id, idx)
            var = model.new_bool_var(f"x_{session.id}_{idx}")
            variables[key], candidate_map[key] = var, (room_id, day, start, periods, session)
            for p in periods:
                by_room_slot[room_id, day, p].append(var)
                for f in session.faculty_ids: by_faculty_slot[f, day, p].append(var)
                for g in session.group_ids: by_group_slot[g, day, p].append(var)
            for f in session.faculty_ids: by_faculty_day[f, day].append((var, len(periods)))
            by_offering_day[session.offering_id, day].append(var)
            start_by_session_day[session.id, day].append(var)
            preference = sum(problem.faculty[f].preferences.get((day, p), 0) for f in session.faculty_ids for p in periods)
            cost = max(0, -preference) * problem.weights.get("preference", 3)
            if session.preferred_periods and start not in session.preferred_periods:
                cost += problem.weights.get("preference", 3)
            cost += max(0, start - 5) * problem.weights.get("late", 1)
            if cost: penalties.append(cost * var)
        session_vars = [v for (sid, _), v in variables.items() if sid == session.id]
        if not session_vars:
            diagnostics.append({"code": "reservation_conflict", "session": session.id, "message": f"{session.code} has no candidate after fixed reservations are applied."})
        else:
            model.add_exactly_one(session_vars)
    if diagnostics:
        return SolveResult("invalid_input", [], None, perf_counter() - started, diagnostics)
    for (room_id, _, _), vs in by_room_slot.items(): model.add(sum(vs) <= problem.rooms[room_id].concurrent_capacity)
    for vs in by_faculty_slot.values(): model.add_at_most_one(vs)
    for vs in by_group_slot.values(): model.add_at_most_one(vs)
    for (faculty_id, _), pairs in by_faculty_day.items():
        model.add(sum(v * periods for v, periods in pairs) <= problem.faculty[faculty_id].daily_limit)
    for (_, _), vs in by_offering_day.items():
        if len(vs) > 1:
            excess = model.new_int_var(0, len(vs), "same_day_excess")
            model.add(excess >= sum(vs) - 1)
            penalties.append(problem.weights.get("same_day", 4) * excess)
    parallel_groups = defaultdict(list)
    for s in problem.sessions:
        if s.parallel_key: parallel_groups[s.parallel_key].append(s)
    for sessions in parallel_groups.values():
        for day in problem.days:
            base = start_by_session_day.get((sessions[0].id, day), [])
            for other in sessions[1:]:
                model.add(sum(base) == sum(start_by_session_day.get((other.id, day), [])))
        for period in problem.periods:
            base_vars = [v for k, v in variables.items() if k[0] == sessions[0].id and candidate_map[k][2] == period]
            for other in sessions[1:]:
                other_vars = [v for k, v in variables.items() if k[0] == other.id and candidate_map[k][2] == period]
                model.add(sum(base_vars) == sum(other_vars))
    model.minimize(sum(penalties))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.random_seed = random_seed
    solver.parameters.num_search_workers = 1
    result_status = solver.solve(model)
    status = STATUS.get(result_status, "unknown")
    assignments = []
    if status in {"optimal", "feasible"}:
        for key, var in variables.items():
            if solver.boolean_value(var):
                room_id, day, start, _, s = candidate_map[key]
                assignments.append(Assignment(s.id, s.offering_id, s.occurrence, day, start, s.duration, room_id, s.faculty_ids, s.group_ids))
    elif status == "infeasible":
        diagnostics.append({"code": "solver_infeasible", "message": "CP-SAT proved that no schedule satisfies all configured hard constraints."})
    elif status == "unknown":
        diagnostics.append({"code": "solver_unknown", "message": "No solution was found within the time limit; infeasibility was not proven."})
    return SolveResult(status, assignments, solver.objective_value if assignments else None, perf_counter() - started, diagnostics, {"branches": solver.num_branches, "conflicts": solver.num_conflicts})

