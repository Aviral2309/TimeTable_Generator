from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from sqlalchemy.orm import Session

from app.models.entities import Timetable, TimetableBackup
from app.scheduling.domain import Assignment


def create_timetable_backup(
    db: Session,
    table: Timetable,
    assignments: list[Assignment],
    metrics: dict,
    reason: str = "automatic_generation",
) -> TimetableBackup:
    snapshot = {
        "format": "sgsits-timetable-backup-v1",
        "timetable_id": table.id,
        "academic_year_id": table.academic_year_id,
        "version": table.version,
        "status": table.status,
        "metrics": metrics,
        "sessions": [asdict(assignment) for assignment in assignments],
    }
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    backup = TimetableBackup(
        timetable_id=table.id,
        academic_year_id=table.academic_year_id,
        version=table.version,
        reason=reason,
        checksum=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        snapshot=snapshot,
    )
    db.add(backup)
    return backup
