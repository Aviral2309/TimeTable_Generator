"""Upgrade a legacy SQLite database that predates Alembic revision tracking."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: migrate_legacy_session_components.py DATABASE_PATH")
    database = Path(sys.argv[1]).resolve()
    connection = sqlite3.connect(database)
    try:
        course_columns = columns(connection, "course_offerings")
        additions = {
            "theory_sessions_per_week": "INTEGER NOT NULL DEFAULT 0",
            "lecture_sessions_per_week": "INTEGER NOT NULL DEFAULT 0",
            "theory_faculty_ids": "JSON NOT NULL DEFAULT '[]'",
            "lecture_faculty_ids": "JSON NOT NULL DEFAULT '[]'",
        }
        for name, definition in additions.items():
            if name not in course_columns:
                connection.execute(f"ALTER TABLE course_offerings ADD COLUMN {name} {definition}")
        connection.execute(
            "UPDATE course_offerings SET theory_sessions_per_week = sessions_per_week, "
            "theory_faculty_ids = faculty_ids WHERE kind <> 'lab' AND theory_sessions_per_week = 0 "
            "AND lecture_sessions_per_week = 0"
        )
        if "session_type" not in columns(connection, "timetable_sessions"):
            connection.execute(
                "ALTER TABLE timetable_sessions ADD COLUMN session_type VARCHAR(20) NOT NULL DEFAULT 'theory'"
            )
        connection.execute(
            "UPDATE timetable_sessions SET session_type = 'lab' WHERE course_offering_id IN "
            "(SELECT id FROM course_offerings WHERE kind = 'lab')"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS alembic_version "
            "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
        )
        connection.execute("DELETE FROM alembic_version")
        connection.execute(
            "INSERT INTO alembic_version(version_num) VALUES ('f7d8130c9a42')"
        )
        connection.commit()
        print(f"Upgraded {database} to f7d8130c9a42")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
