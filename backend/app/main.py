from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.auth import router as auth_router
from app.api.master_data import router as master_data_router
from app.core.config import get_settings
from app.db.session import Base, engine
from app import models  # noqa: F401

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", description="Phase 1 scheduling engine and generation API")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")], allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
app.include_router(router)
app.include_router(auth_router)
app.include_router(master_data_router)


@app.on_event("startup")
def create_local_schema():
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)

