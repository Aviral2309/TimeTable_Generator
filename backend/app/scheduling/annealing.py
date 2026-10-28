from __future__ import annotations
import math
import random
from dataclasses import replace
from app.scheduling.domain import Assignment, Problem
from app.scheduling.preprocessing import candidates_for
from app.scheduling.validator import calculate_metrics, validate_schedule


def soft_cost(problem: Problem, schedule: list[Assignment]) -> float:
    metrics = calculate_metrics(problem, schedule)
    return (
        metrics["student_gaps"] * problem.weights.get("student_gaps", 100)
        + metrics["cohort_gaps"] * problem.weights.get("cohort_gaps", 300)
        + metrics["faculty_gaps"] * problem.weights.get("faculty_gaps", 5)
        + metrics["late_student_periods"] * problem.weights.get("late_student_periods", 10)
        + metrics["isolated_student_days"] * problem.weights.get("isolated_student_days", 8)
        + metrics["cohort_single_period_days"] * problem.weights.get("cohort_single_period_days", 300)
        + metrics["cohort_daily_load_imbalance"] * problem.weights.get("cohort_daily_load_imbalance", 12)
        + metrics["cohort_overloaded_days"] * problem.weights.get("cohort_overloaded_days", 100)
        + metrics["student_room_changes"] * problem.weights.get("student_room_changes", 30)
    )


def refine(problem: Problem, initial: list[Assignment], iterations: int = 500, seed: int = 42) -> tuple[list[Assignment], dict]:
    rng = random.Random(seed)
    current, best = list(initial), list(initial)
    current_cost = best_cost = soft_cost(problem, current)
    accepted = improvements = 0
    sessions = {s.id: s for s in problem.sessions}
    temperature = max(1.0, current_cost * 0.25)
    for step in range(iterations):
        idx = rng.randrange(len(current))
        old = current[idx]
        session = sessions[old.session_id]
        choices = list(candidates_for(problem, session))
        if not choices: continue
        room, day, start, _ = rng.choice(choices)
        candidate = list(current)
        candidate[idx] = replace(old, room_id=room, day=day, start_period=start)
        valid, _, _ = validate_schedule(problem, candidate)
        if not valid: continue
        cost = soft_cost(problem, candidate)
        delta = cost - current_cost
        if delta <= 0 or rng.random() < math.exp(-delta / max(temperature, 0.001)):
            current, current_cost, accepted = candidate, cost, accepted + 1
            if cost < best_cost:
                best, best_cost, improvements = list(candidate), cost, improvements + 1
        temperature *= 0.995
    return best, {"initial_cost": soft_cost(problem, initial), "best_cost": best_cost, "iterations": iterations, "accepted_moves": accepted, "improvements": improvements, "seed": seed}


def refine_with_change_budget(
    problem: Problem,
    initial: list[Assignment],
    baseline: list[Assignment],
    iterations: int = 4000,
    seed: int = 42,
    extra_change_budget: int = 6,
    change_cost: int = 100,
) -> tuple[list[Assignment], dict]:
    """Improve quality with a small, explicit disruption budget.

    CP-SAT supplies the minimum feasible change count.  A few supporting moves
    are allowed only when their quality improvement outweighs ``change_cost``;
    this prevents a nominal one-class repair from creating large student gaps.
    """
    baseline_map = {
        assignment.session_id: (assignment.room_id, assignment.day, assignment.start_period)
        for assignment in baseline
    }

    def change_count(schedule: list[Assignment]) -> int:
        return sum(
            baseline_map.get(assignment.session_id)
            != (assignment.room_id, assignment.day, assignment.start_period)
            for assignment in schedule
        )

    minimum_changes = change_count(initial)
    max_changes = min(len(initial), minimum_changes + extra_change_budget)

    def score(schedule: list[Assignment]) -> float:
        return soft_cost(problem, schedule) + change_count(schedule) * change_cost

    rng = random.Random(seed)
    current, best = list(initial), list(initial)
    current_cost = best_cost = score(current)
    accepted = improvements = evaluated = 0
    sessions = {session.id: session for session in problem.sessions}
    # Deterministically inspect every placement of sessions CP-SAT already
    # decided must move.  This guarantees the best one-session repair instead
    # of depending on random neighbourhood coverage.
    changed_indices = [
        index
        for index, assignment in enumerate(current)
        if baseline_map.get(assignment.session_id)
        != (assignment.room_id, assignment.day, assignment.start_period)
    ]
    for idx in changed_indices:
        old = current[idx]
        session = sessions[old.session_id]
        for room, day, start, _ in candidates_for(problem, session):
            candidate = list(current)
            candidate[idx] = replace(old, room_id=room, day=day, start_period=start)
            if change_count(candidate) > max_changes:
                continue
            valid, _, _ = validate_schedule(problem, candidate)
            if not valid:
                continue
            evaluated += 1
            cost = score(candidate)
            if cost < best_cost:
                best, best_cost, improvements = list(candidate), cost, improvements + 1
        current, current_cost = list(best), best_cost
    temperature = max(1.0, current_cost * 0.15)
    for _ in range(iterations):
        idx = rng.randrange(len(current))
        old = current[idx]
        session = sessions[old.session_id]
        choices = list(candidates_for(problem, session))
        if not choices:
            continue
        room, day, start, _ = rng.choice(choices)
        candidate = list(current)
        candidate[idx] = replace(old, room_id=room, day=day, start_period=start)
        if change_count(candidate) > max_changes:
            continue
        valid, _, _ = validate_schedule(problem, candidate)
        if not valid:
            continue
        cost = score(candidate)
        delta = cost - current_cost
        if delta <= 0 or rng.random() < math.exp(-delta / max(temperature, 0.001)):
            current, current_cost, accepted = candidate, cost, accepted + 1
            if cost < best_cost:
                best, best_cost, improvements = list(candidate), cost, improvements + 1
        temperature *= 0.997
    return best, {
        "strategy": "bounded_change_quality_refinement",
        "minimum_changes": minimum_changes,
        "change_budget": max_changes,
        "change_cost": change_cost,
        "initial_cost": soft_cost(problem, initial),
        "best_cost": soft_cost(problem, best),
        "best_changes": change_count(best),
        "best_combined_cost": best_cost,
        "iterations": iterations,
        "accepted_moves": accepted,
        "improvements": improvements,
        "evaluated_placements": evaluated,
        "seed": seed,
    }

