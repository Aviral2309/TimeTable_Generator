from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import bootstrap_admin, bootstrap_status
from app.api.setup import create_academic_year, create_department, create_institute, create_working_week, setup_status
from app.db.session import Base
from app.models.entities import User
from app.schemas.auth import BootstrapAdminRequest
from app.schemas.setup import AcademicYearCreate, DepartmentCreate, InstituteCreate, WorkingWeekCreate


def empty_database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_empty_installation_bootstraps_only_the_first_admin():
    db = empty_database()
    assert bootstrap_status(db)["needs_admin"] is True
    response = bootstrap_admin(BootstrapAdminRequest(name="System Admin", email="admin@college.edu", password="strong-pass"), db)
    assert response.user.role == "admin"
    assert bootstrap_status(db)["needs_admin"] is False
    assert db.query(User).count() == 1


def test_setup_status_starts_empty_and_tracks_admin_foundation():
    db = empty_database()
    actor = User(email="admin@college.edu", name="Admin", password_hash="x", role="admin")
    initial = setup_status(db, actor)
    assert initial["ready_for_validation"] is False
    assert all(value == 0 for value in initial["counts"].values())

    create_institute(InstituteCreate(name="Example Institute"), db, actor)
    create_department(DepartmentCreate(code="EE", name="Electrical Engineering"), db, actor)
    create_academic_year(AcademicYearCreate(name="2026-27"), db, actor)
    create_working_week(WorkingWeekCreate(days=["Monday", "Tuesday"], start_hour=10, periods_per_day=6, lunch_after_period=3), db, actor)

    configured = setup_status(db, actor)
    assert configured["counts"]["time_slots"] == 12
    assert configured["steps"][0]["complete"] is True
    assert configured["ready_for_validation"] is False
