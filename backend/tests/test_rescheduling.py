from sqlalchemy import select

from app.models.entities import CourseOffering, RescheduleEvent, Timetable, TimetableBackup, TimetableSession
from app.api.routes import timetable_by_id, timetable_delete, timetable_history, timetable_validation
from app.models.entities import User
from fastapi import HTTPException
import pytest
from app.schemas.rescheduling import RescheduleRequest
from app.services.generation import best_compatible_assignments, generate_problem
from app.scheduling.database_problem import build_database_problem
from app.scheduling.validator import validate_schedule
from app.services.rescheduling import apply_reschedule, plan_reschedule
from test_database_generation import configured_problem


def disruption_for_first_theory(db, table):
    offering = db.scalar(select(CourseOffering).where(CourseOffering.code == "EE301"))
    scheduled = db.scalar(select(TimetableSession).where(
        TimetableSession.timetable_id == table.id,
        TimetableSession.course_offering_id == offering.id,
    ))
    return RescheduleRequest(
        source_timetable_id=table.id,
        resource_type="faculty",
        resource_id=offering.faculty_ids[0],
        day=scheduled.day,
        start_period=scheduled.start_period,
        duration_periods=scheduled.duration_periods,
        reason="Faculty duty leave",
        time_limit_seconds=10,
        random_seed=7,
    )


def test_dynamic_rescheduling_moves_the_affected_class_and_preserves_validity():
    db, year, semester_ids = configured_problem()
    generated = generate_problem(db, year.id, "cp_sat", 10, 42, semester_ids)
    assert generated["valid"]
    table = db.scalar(select(Timetable).order_by(Timetable.id.desc()))
    backup = db.scalar(select(TimetableBackup).where(TimetableBackup.timetable_id == table.id))
    assert backup and backup.snapshot["format"] == "sgsits-timetable-backup-v1"
    assert len(backup.snapshot["sessions"]) == len(generated["assignments"])
    request = disruption_for_first_theory(db, table)

    proposal = plan_reschedule(db, request)

    assert proposal["valid"], proposal["diagnostics"]
    assert proposal["affected_sessions"] >= 1
    assert proposal["moved_sessions"] >= 1
    affected = set(proposal["affected_session_ids"])
    assert any(change["session_id"] in affected for change in proposal["changes"])
    assert proposal["refinement"]["best_changes"] <= proposal["refinement"]["change_budget"]
    assert proposal["refinement"]["best_combined_cost"] <= (
        proposal["refinement"]["initial_cost"]
        + proposal["refinement"]["minimum_changes"] * proposal["refinement"]["change_cost"]
    )


def test_saved_timetable_can_be_reused_as_a_valid_quality_warm_start():
    db, year, semester_ids = configured_problem()
    generated = generate_problem(db, year.id, "cp_sat", 10, 42, semester_ids)
    problem = build_database_problem(db, year.id, semester_ids)

    previous = best_compatible_assignments(db, problem, year.id)

    assert generated["valid"] and previous is not None
    assert validate_schedule(problem, previous)[0]
    assert len(previous) == len(problem.sessions)


def test_applying_reschedule_creates_a_new_version_and_history_event():
    db, year, semester_ids = configured_problem()
    generate_problem(db, year.id, "cp_sat", 10, 42, semester_ids)
    source = db.scalar(select(Timetable).order_by(Timetable.id.desc()))
    request = disruption_for_first_theory(db, source)

    result = apply_reschedule(db, request, None)

    assert result["valid"]
    assert result["result_version"] == source.version + 1
    assert db.scalar(select(RescheduleEvent)).result_timetable_id == result["result_timetable_id"]
    backup = db.scalar(select(TimetableBackup).where(TimetableBackup.timetable_id == result["result_timetable_id"]))
    assert backup and backup.reason == "automatic_reschedule"


def test_every_generated_timetable_exposes_its_validation_report():
    db, year, semester_ids = configured_problem()
    generated = generate_problem(db, year.id, "cp_sat", 10, 42, semester_ids)
    table = db.scalar(select(Timetable).order_by(Timetable.id.desc()))
    actor = type("Actor", (), {"role": "admin"})()

    report = timetable_validation(table.id, db, actor)

    assert generated["valid"] and report["valid"]
    assert report["scheduled_sessions"] == len(generated["assignments"])
    assert report["metrics"]["scheduled_sessions"] == len(generated["assignments"])


def test_non_admins_can_read_only_published_timetable_versions():
    db, year, semester_ids = configured_problem()
    generate_problem(db, year.id, "cp_sat", 10, 42, semester_ids)
    table = db.scalar(select(Timetable).order_by(Timetable.id.desc()))
    faculty = User(email="reader@sgsits.ac.in", name="Reader", password_hash="x", role="faculty", faculty_id=1)

    assert timetable_history(None, db, faculty)["items"] == []
    with pytest.raises(HTTPException) as error:
        timetable_by_id(table.id, db, faculty)
    assert error.value.status_code == 403

    table.status = "published"; db.commit()
    assert timetable_history(None, db, faculty)["items"][0]["id"] == table.id
    assert timetable_by_id(table.id, db, faculty)["id"] == table.id


def test_admin_can_delete_draft_or_published_timetable():
    db, year, semester_ids = configured_problem()
    generate_problem(db, year.id, "cp_sat", 10, 42, semester_ids)
    table = db.scalar(select(Timetable).order_by(Timetable.id.desc()))
    admin = User(email="admin@sgsits.ac.in", name="Admin", password_hash="x", role="admin")

    table.status = "published"; db.commit()
    timetable_delete(table.id, db, admin)
    assert db.get(Timetable, table.id) is None
    assert db.scalar(select(TimetableSession).where(TimetableSession.timetable_id == table.id)) is None
    assert db.scalar(select(TimetableBackup).where(TimetableBackup.timetable_id == table.id)) is None
