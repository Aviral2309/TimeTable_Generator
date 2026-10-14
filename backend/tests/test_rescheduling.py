from sqlalchemy import select

from app.models.entities import CourseOffering, RescheduleEvent, Timetable, TimetableBackup, TimetableSession
from app.schemas.rescheduling import RescheduleRequest
from app.services.generation import generate_problem
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
    assert backup and backup.snapshot["format"] == "chronos-timetable-backup-v1"
    assert len(backup.snapshot["sessions"]) == len(generated["assignments"])
    request = disruption_for_first_theory(db, table)

    proposal = plan_reschedule(db, request)

    assert proposal["valid"], proposal["diagnostics"]
    assert proposal["affected_sessions"] >= 1
    assert proposal["moved_sessions"] >= 1
    affected = set(proposal["affected_session_ids"])
    assert any(change["session_id"] in affected for change in proposal["changes"])


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
