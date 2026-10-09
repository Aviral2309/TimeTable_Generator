import os
os.environ["DATABASE_URL"] = "sqlite://"

from app.db.session import Base, engine
from app.api.routes import generate, health
from app.db.session import SessionLocal
from app.schemas.generation import GenerationRequest
from app.models.entities import User
from fastapi import HTTPException
import pytest


Base.metadata.create_all(engine)
def test_health():
    assert health() == {"status": "ok"}


def test_generation_endpoint_rejects_demo_fallback():
    db = SessionLocal()
    try:
        actor = User(id=99, email="admin@test.edu", name="Admin", password_hash="x", role="admin")
        with pytest.raises(HTTPException) as exc:
            generate(GenerationRequest(solver_mode="cp_sat", time_limit_seconds=15, random_seed=7), db, actor)
    finally:
        db.close()
    assert exc.value.status_code == 422
    assert "demo fallback is disabled" in exc.value.detail

