import os
os.environ["DATABASE_URL"] = "sqlite://"

from app.db.session import Base, engine
from app.api.routes import generate, health
from app.db.session import SessionLocal
from app.schemas.generation import GenerationRequest, GenerationResponse
from app.models.entities import User


Base.metadata.create_all(engine)
def test_health():
    assert health() == {"status": "ok"}


def test_generation_endpoint_returns_valid_schedule():
    db = SessionLocal()
    try:
        actor = User(id=99, email="admin@test.edu", name="Admin", password_hash="x", role="admin")
        data = generate(GenerationRequest(solver_mode="cp_sat", time_limit_seconds=15, random_seed=7), db, actor)
    finally:
        db.close()
    data = GenerationResponse.model_validate(data).model_dump()
    assert data["status"] in {"optimal", "feasible"}
    assert data["valid"] is True
    assert data["run_id"]

