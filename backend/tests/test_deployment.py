from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deployment import inspect_database
from app.core.security import hash_password
from app.db.session import Base
from app.models.entities import User


def backup_database(path: Path, *, include_admin: bool) -> Path:
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    if include_admin:
        db = sessionmaker(bind=engine)()
        db.add(User(email="admin@sgsits.ac.in", name="Admin", password_hash=hash_password("secret123"), role="admin", active=True))
        db.commit(); db.close()
    engine.dispose()
    return path


def test_private_backup_manifest_requires_an_active_admin():
    valid_path = Path("deployment-test-valid.db")
    starter_path = Path("deployment-test-starter.db")
    valid_path.unlink(missing_ok=True); starter_path.unlink(missing_ok=True)
    try:
        valid = inspect_database(backup_database(valid_path, include_admin=True))
        assert valid["active_admins"] == 1 and valid["timetables"] == 0

        with pytest.raises(HTTPException) as error:
            inspect_database(backup_database(starter_path, include_admin=False))
        assert error.value.status_code == 422
    finally:
        valid_path.unlink(missing_ok=True); starter_path.unlink(missing_ok=True)
