"""dynamic rescheduling history

Revision ID: c81f3a2d904b
Revises: 6b82e208d57a
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c81f3a2d904b"
down_revision: Union[str, None] = "6b82e208d57a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reschedule_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_timetable_id", sa.Integer(), nullable=False),
        sa.Column("result_timetable_id", sa.Integer(), nullable=True),
        sa.Column("resource_type", sa.String(length=20), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.String(length=12), nullable=False),
        sa.Column("start_period", sa.Integer(), nullable=False),
        sa.Column("duration_periods", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("affected_sessions", sa.Integer(), nullable=False),
        sa.Column("moved_sessions", sa.Integer(), nullable=False),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["result_timetable_id"], ["timetables.id"]),
        sa.ForeignKeyConstraint(["source_timetable_id"], ["timetables.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reschedule_events_source_timetable_id"), "reschedule_events", ["source_timetable_id"], unique=False)
    op.create_index(op.f("ix_reschedule_events_result_timetable_id"), "reschedule_events", ["result_timetable_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reschedule_events_result_timetable_id"), table_name="reschedule_events")
    op.drop_index(op.f("ix_reschedule_events_source_timetable_id"), table_name="reschedule_events")
    op.drop_table("reschedule_events")
