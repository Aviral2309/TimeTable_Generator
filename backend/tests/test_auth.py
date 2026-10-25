import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.api.auth import change_password, login
from app.api.master_data import room_create
from app.core.security import decode_token, hash_password, require_roles, verify_password
from app.db.session import Base
from app.models.entities import Department, Room, User
from app.schemas.auth import LoginRequest, PasswordChangeRequest, UserCreate
from app.schemas.master_data import RoomCreate


def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_password_hash_is_salted_and_verifies():
    first, second = hash_password("Demo@123"), hash_password("Demo@123")
    assert first != second
    assert verify_password("Demo@123", first)
    assert not verify_password("wrong", first)


def test_login_issues_signed_role_token():
    db = session(); user = User(email="admin@test.edu", name="Admin", password_hash=hash_password("secret123"), role="admin")
    db.add(user); db.commit()
    result = login(LoginRequest(email="admin@test.edu", password="secret123"), db)
    assert result.user.role == "admin"
    assert decode_token(result.access_token)["sub"] == user.id


def test_wrong_password_is_rejected():
    db = session(); db.add(User(email="user@test.edu", name="User", password_hash=hash_password("right"), role="student")); db.commit()
    with pytest.raises(HTTPException) as error: login(LoginRequest(email="user@test.edu", password="wrong"), db)
    assert error.value.status_code == 401


def test_selected_workspace_must_match_the_account_role():
    db = session(); db.add(User(email="faculty@sgsits.ac.in", name="Faculty", password_hash=hash_password("right"), role="faculty")); db.commit()
    with pytest.raises(HTTPException) as error:
        login(LoginRequest(email="faculty@sgsits.ac.in", password="right", role="admin"), db)
    assert error.value.status_code == 403
    assert "Faculty" in error.value.detail


def test_student_cannot_pass_admin_role_check():
    dependency = require_roles("admin")
    with pytest.raises(HTTPException) as error: dependency(User(email="s@test.edu", name="Student", password_hash="x", role="student"))
    assert error.value.status_code == 403


def test_faculty_cannot_pass_admin_role_check():
    dependency = require_roles("admin")
    with pytest.raises(HTTPException) as error: dependency(User(email="f@sgsits.ac.in", name="Faculty", password_hash="x", role="faculty"))
    assert error.value.status_code == 403


def test_admin_can_create_room():
    db = session(); department = Department(code="EE", name="Electrical Engineering"); db.add(department); db.commit()
    admin = User(email="a@test.edu", name="Admin", password_hash="x", role="admin")
    room = room_create(RoomCreate(code="EE-X", name="New Room", department_id=department.id, capacity=55, room_type="theory", features=["projector"]), db, admin)
    assert room.id and db.query(Room).count() == 1


def test_new_role_accounts_require_sgsits_email_domain():
    with pytest.raises(ValueError):
        UserCreate(name="Student", email="student@gmail.com", password="secret123", role="student", student_group_id="SEM-3")
    account = UserCreate(name="Student", email="student@sgsits.ac.in", password="secret123", role="student", student_group_id="SEM-3")
    assert str(account.email) == "student@sgsits.ac.in"


def test_authenticated_user_can_change_only_with_current_password():
    db = session(); user = User(email="faculty@sgsits.ac.in", name="Faculty", password_hash=hash_password("old-secret"), role="faculty")
    db.add(user); db.commit()
    with pytest.raises(HTTPException) as error:
        change_password(PasswordChangeRequest(current_password="wrong", new_password="new-secret"), db, user)
    assert error.value.status_code == 400
    result = change_password(PasswordChangeRequest(current_password="old-secret", new_password="new-secret"), db, user)
    assert result["message"] and verify_password("new-secret", user.password_hash)

