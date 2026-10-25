from datetime import UTC, datetime
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from app.core.security import require_roles
from app.db.session import engine
from app.models.entities import User


router = APIRouter(prefix="/api/deployment", tags=["Deployment & backup"])
MAX_BACKUP_BYTES = 100 * 1024 * 1024
REQUIRED_TABLES = {
    "users", "institutes", "departments", "academic_years", "faculty", "rooms",
    "time_slots", "semester_offerings", "course_offerings", "generation_runs",
    "timetables", "timetable_sessions", "validation_reports",
}


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


def inspect_database(path: Path, *, require_admin: bool = True) -> dict:
    try:
        with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise HTTPException(422, "Backup database failed its integrity check")
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            missing = sorted(REQUIRED_TABLES - tables)
            if missing:
                raise HTTPException(422, f"Backup is not a compatible timetable database; missing: {', '.join(missing)}")
            active_admins = connection.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]
            if require_admin and not active_admins:
                raise HTTPException(422, "A private backup must contain at least one active administrator")
            return {
                "active_admins": active_admins,
                "faculty": connection.execute("SELECT COUNT(*) FROM faculty").fetchone()[0],
                "rooms": connection.execute("SELECT COUNT(*) FROM rooms").fetchone()[0],
                "subjects": connection.execute("SELECT COUNT(*) FROM course_offerings").fetchone()[0],
                "timetables": connection.execute("SELECT COUNT(*) FROM timetables").fetchone()[0],
            }
    except sqlite3.DatabaseError as exc:
        raise HTTPException(422, "Uploaded file is not a readable SQLite database") from exc


def restore_sqlite_database(uploaded: Path) -> tuple[dict, str]:
    source = _sqlite_source()
    manifest = inspect_database(uploaded)
    rollback_dir = source.parent / "backups"
    rollback_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    rollback = rollback_dir / f"pre-restore-{stamp}.db"
    with closing(sqlite3.connect(source)) as current, closing(sqlite3.connect(rollback)) as saved:
        current.backup(saved)
    try:
        engine.dispose()
        with closing(sqlite3.connect(uploaded)) as incoming, closing(sqlite3.connect(source)) as destination:
            incoming.backup(destination)
            destination.execute("PRAGMA foreign_keys = ON")
        inspect_database(source)
    except Exception:
        engine.dispose()
        with closing(sqlite3.connect(rollback)) as saved, closing(sqlite3.connect(source)) as destination:
            saved.backup(destination)
        raise
    finally:
        engine.dispose()
    return manifest, rollback.name


@router.get("/database-backup")
def download_database_backup(_: User = Depends(require_roles("admin"))):
    """Private operational backup, including user accounts and password hashes."""
    return _database_download(starter=False)


@router.get("/starter-database")
def download_starter_database(_: User = Depends(require_roles("admin"))):
    """Reusable department dataset with all login accounts removed."""
    return _database_download(starter=True)


@router.post("/restore-database")
async def restore_database(file: UploadFile = File(...), _: User = Depends(require_roles("admin"))):
    """Restore a verified private SQLite backup and retain an automatic rollback copy."""
    if engine.url.get_backend_name() != "sqlite":
        raise HTTPException(409, "Database-file restoration is available only for SQLite installations")
    suffix = Path(file.filename or "backup.db").suffix.lower()
    if suffix not in {".db", ".sqlite", ".sqlite3"}:
        raise HTTPException(422, "Select a .db, .sqlite, or .sqlite3 backup file")
    temporary = tempfile.NamedTemporaryFile(prefix="sgsits-restore-", suffix=".db", delete=False)
    target = Path(temporary.name)
    size = 0
    try:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_BACKUP_BYTES:
                raise HTTPException(413, "Backup file exceeds the 100 MB safety limit")
            temporary.write(chunk)
        temporary.close()
        manifest, rollback = restore_sqlite_database(target)
        return {"message": "Database restored successfully. Sign in again.", "rollback_backup": rollback, "manifest": manifest}
    finally:
        if not temporary.closed: temporary.close()
        target.unlink(missing_ok=True)
