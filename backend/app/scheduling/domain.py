from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Slot:
    day: str
    period: int
    blocked: bool = False


@dataclass(frozen=True)
class ResourceReservation:
    day: str
    periods: tuple[int, ...]
    room_id: int | None = None
    faculty_id: int | None = None
    group_id: str | None = None
    description: str = ""


@dataclass(frozen=True)
class RoomResource:
    id: int
    code: str
    capacity: int
    kind: str
    features: frozenset[str] = frozenset()
    concurrent_capacity: int = 1
    unavailable: frozenset[tuple[str, int]] = frozenset()


@dataclass(frozen=True)
class FacultyResource:
    id: int
    code: str
    weekly_limit: int = 18
    daily_limit: int = 6
    unavailable: frozenset[tuple[str, int]] = frozenset()
    preferences: dict[tuple[str, int], int] = field(default_factory=dict)


@dataclass(frozen=True)
class RequiredSession:
    id: str
    offering_id: int
    occurrence: int
    code: str
    kind: str
    duration: int
    enrollment: int
    faculty_ids: tuple[int, ...]
    group_ids: tuple[str, ...]
    eligible_room_ids: tuple[int, ...]
    required_features: frozenset[str] = frozenset()
    preferred_periods: frozenset[int] = frozenset()
    fixed_day: str | None = None
    fixed_period: int | None = None
    fixed_room_id: int | None = None
    parallel_key: str | None = None
    cohort_id: str | None = None
    is_elective: bool = False


@dataclass(frozen=True)
class Assignment:
    session_id: str
    offering_id: int
    occurrence: int
    day: str
    start_period: int
    duration: int
    room_id: int
    faculty_ids: tuple[int, ...]
    group_ids: tuple[str, ...]


@dataclass
class Problem:
    days: list[str]
    periods: list[int]
    blocked_slots: set[tuple[str, int]]
    rooms: dict[int, RoomResource]
    faculty: dict[int, FacultyResource]
    sessions: list[RequiredSession]
    reservations: list[ResourceReservation]
    weights: dict[str, int] = field(default_factory=lambda: {"preference": 3, "late": 1, "same_day": 4})


@dataclass
class SolveResult:
    status: str
    assignments: list[Assignment]
    objective: float | None
    runtime_seconds: float
    diagnostics: list[dict]
    statistics: dict = field(default_factory=dict)

