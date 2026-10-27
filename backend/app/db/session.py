from pathlib import Path
import shutil

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()


def install_starter_database(database_url: str, enabled: bool = True, project_root: Path | None = None) -> Path | None:
    """Install the sanitized department dataset for a brand-new local clone."""
    url = make_url(database_url)
    if not enabled or url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return None
    target = Path(url.database)
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    root = project_root or Path(__file__).resolve().parents[3]
    starter = root / "starter" / "sgsits-department-starter.db"
    if target.exists() or not starter.is_file():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(starter, target)
    return target


install_starter_database(settings.database_url, settings.install_starter_database)
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine_options = {"connect_args": connect_args}
if settings.database_url == "sqlite://":
    engine_options["poolclass"] = StaticPool
engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

