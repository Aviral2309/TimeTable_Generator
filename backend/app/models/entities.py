from __future__ import annotations
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class RoomType(StrEnum):
    THEORY = "theory"
    LAB = "lab"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    MODEL_INVALID = "model_invalid"
    UNKNOWN = "unknown"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(20), index=True)
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"), unique=True)
    student_group_id: Mapped[str | None] = mapped_column(String(80))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Institute(Base):
    __tablename__ = "institutes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)


class AcademicYear(Base):
    __tablename__ = "academic_years"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    term_type: Mapped[str] = mapped_column(String(10), default="odd")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Faculty(Base):
    __tablename__ = "faculty"
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    home_department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    weekly_limit: Mapped[int] = mapped_column(Integer, default=18)
    daily_limit: Mapped[int] = mapped_column(Integer, default=6)
    max_consecutive: Mapped[int] = mapped_column(Integer, default=3)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    capacity: Mapped[int] = mapped_column(Integer)
    room_type: Mapped[str] = mapped_column(String(20))
    features: Mapped[list[str]] = mapped_column(JSON, default=list)
    concurrent_capacity: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TimeSlot(Base):
    __tablename__ = "time_slots"
    __table_args__ = (UniqueConstraint("day", "period_index"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[str] = mapped_column(String(12), index=True)
    period_index: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)


class SemesterOffering(Base):
    __tablename__ = "semester_offerings"
    __table_args__ = (UniqueConstraint("academic_year_id", "department_id", "semester_number", name="uq_single_semester_cohort"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    semester_number: Mapped[int] = mapped_column(Integer)
    section: Mapped[str] = mapped_column(String(10), default="ALL")
    strength: Mapped[int] = mapped_column(Integer)
    home_room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))
    home_room_policy: Mapped[str] = mapped_column(String(10), default="hard")


class CourseOffering(Base):
    __tablename__ = "course_offerings"
    id: Mapped[int] = mapped_column(primary_key=True)
    semester_offering_id: Mapped[int] = mapped_column(ForeignKey("semester_offerings.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(150))
    kind: Mapped[str] = mapped_column(String(20), default="theory")
    sessions_per_week: Mapped[int] = mapped_column(Integer, default=1)
    theory_sessions_per_week: Mapped[int] = mapped_column(Integer, default=0)
    lecture_sessions_per_week: Mapped[int] = mapped_column(Integer, default=0)
    duration_periods: Mapped[int] = mapped_column(Integer, default=1)
    enrollment: Mapped[int] = mapped_column(Integer)
    faculty_ids: Mapped[list[int]] = mapped_column(JSON)
    theory_faculty_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    lecture_faculty_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    participant_group_ids: Mapped[list[str]] = mapped_column(JSON)
    eligible_room_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    required_features: Mapped[list[str]] = mapped_column(JSON, default=list)
    elective_group: Mapped[str | None] = mapped_column(String(50))
    parallel_elective: Mapped[bool] = mapped_column(Boolean, default=False)
    fixed_day: Mapped[str | None] = mapped_column(String(12))
    fixed_period: Mapped[int | None] = mapped_column(Integer)
    fixed_room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))


class FacultyAvailability(Base):
    __tablename__ = "faculty_availability"
    __table_args__ = (UniqueConstraint("faculty_id", "day", "period_index"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"))
    day: Mapped[str] = mapped_column(String(12))
    period_index: Mapped[int] = mapped_column(Integer)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    preference: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(300), default="")


class RoomAvailability(Base):
    __tablename__ = "room_availability"
    __table_args__ = (UniqueConstraint("room_id", "day", "period_index"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    day: Mapped[str] = mapped_column(String(12))
    period_index: Mapped[int] = mapped_column(Integer)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(String(300), default="")


class FixedReservation(Base):
    __tablename__ = "fixed_reservations"
    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), index=True)
    day: Mapped[str] = mapped_column(String(12))
    start_period: Mapped[int] = mapped_column(Integer)
    duration_periods: Mapped[int] = mapped_column(Integer, default=1)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"))
    participant_group_id: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(250))


class GenerationRun(Base):
    __tablename__ = "generation_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default=RunStatus.QUEUED)
    solver_mode: Mapped[str] = mapped_column(String(30), default="cp_sat")
    weights: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    objective_value: Mapped[float | None] = mapped_column(Float)
    runtime_seconds: Mapped[float | None] = mapped_column(Float)
    diagnostics: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Timetable(Base):
    __tablename__ = "timetables"
    id: Mapped[int] = mapped_column(primary_key=True)
    generation_run_id: Mapped[int] = mapped_column(ForeignKey("generation_runs.id"), unique=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    sessions: Mapped[list[TimetableSession]] = relationship(cascade="all, delete-orphan", back_populates="timetable")


class TimetableSession(Base):
    __tablename__ = "timetable_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    timetable_id: Mapped[int] = mapped_column(ForeignKey("timetables.id", ondelete="CASCADE"), index=True)
    course_offering_id: Mapped[int] = mapped_column(ForeignKey("course_offerings.id"))
    occurrence: Mapped[int] = mapped_column(Integer)
    day: Mapped[str] = mapped_column(String(12))
    start_period: Mapped[int] = mapped_column(Integer)
    duration_periods: Mapped[int] = mapped_column(Integer)
    session_type: Mapped[str] = mapped_column(String(20), default="theory")
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    faculty_ids: Mapped[list[int]] = mapped_column(JSON)
    participant_group_ids: Mapped[list[str]] = mapped_column(JSON)
    timetable: Mapped[Timetable] = relationship(back_populates="sessions")


class TimetableBackup(Base):
    __tablename__ = "timetable_backups"
    id: Mapped[int] = mapped_column(primary_key=True)
    timetable_id: Mapped[int] = mapped_column(ForeignKey("timetables.id", ondelete="CASCADE"), unique=True, index=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(50), default="automatic_generation")
    checksum: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ValidationReport(Base):
    __tablename__ = "validation_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    generation_run_id: Mapped[int] = mapped_column(ForeignKey("generation_runs.id"), index=True)
    valid: Mapped[bool] = mapped_column(Boolean)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class RescheduleEvent(Base):
    __tablename__ = "reschedule_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_timetable_id: Mapped[int] = mapped_column(ForeignKey("timetables.id"), index=True)
    result_timetable_id: Mapped[int | None] = mapped_column(ForeignKey("timetables.id"), index=True)
    resource_type: Mapped[str] = mapped_column(String(20))
    resource_id: Mapped[int] = mapped_column(Integer)
    day: Mapped[str] = mapped_column(String(12))
    start_period: Mapped[int] = mapped_column(Integer)
    duration_periods: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="previewed")
    affected_sessions: Mapped[int] = mapped_column(Integer, default=0)
    moved_sessions: Mapped[int] = mapped_column(Integer, default=0)
    diagnostics: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

