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

