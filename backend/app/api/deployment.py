from datetime import UTC, datetime
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.security import require_roles
from app.db.session import engine
from app.models.entities import User


router = APIRouter(prefix="/api/deployment", tags=["Deployment & backup"])


def _sqlite_source() -> Path:
    if engine.url.get_backend_name() != "sqlite" or not engine.url.database or engine.url.database == ":memory:":
        raise HTTPException(409, "Database file export is available only for file-based SQLite installations")
    source = Path(engine.url.database).resolve()
    if not source.is_file():
        raise HTTPException(404, "The database file could not be found")
    return source


def _database_download(*, starter: bool) -> Response:
    source = _sqlite_source()
    temporary = tempfile.NamedTemporaryFile(prefix="sgsits-timetable-", suffix=".db", delete=False)
    target = Path(temporary.name)
    temporary.close()
    try:
        with closing(sqlite3.connect(source)) as source_connection, closing(sqlite3.connect(target)) as target_connection:
            source_connection.backup(target_connection)
        if starter:
            with closing(sqlite3.connect(target)) as connection:
                connection.execute("PRAGMA foreign_keys = OFF")
                connection.execute("UPDATE reschedule_events SET created_by_user_id = NULL")
                connection.execute("DELETE FROM users")
                try:
                    connection.execute("DELETE FROM sqlite_sequence WHERE name = 'users'")
                except sqlite3.OperationalError:
                    pass
                connection.commit()
                connection.execute("VACUUM")
        payload = target.read_bytes()
    finally:
        target.unlink(missing_ok=True)

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    label = "department-starter" if starter else "private-full-backup"
    return Response(
        content=payload,
        media_type="application/vnd.sqlite3",
        headers={
            "Content-Disposition": f'attachment; filename="sgsits-timetable-{label}-{stamp}.db"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/database-backup")
def download_database_backup(_: User = Depends(require_roles("admin"))):
    """Private operational backup, including user accounts and password hashes."""
    return _database_download(starter=False)


@router.get("/starter-database")
def download_starter_database(_: User = Depends(require_roles("admin"))):
    """Reusable department dataset with all login accounts removed."""
    return _database_download(starter=True)
