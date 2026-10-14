"""automatic timetable backups

Revision ID: b1a34c7e908d
Revises: f7d8130c9a42
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1a34c7e908d"
down_revision: Union[str, None] = "f7d8130c9a42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "timetable_backups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timetable_id", sa.Integer(), nullable=False),
        sa.Column("academic_year_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=50), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["academic_year_id"], ["academic_years.id"]),
        sa.ForeignKeyConstraint(["timetable_id"], ["timetables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("timetable_id"),
    )
    op.create_index(op.f("ix_timetable_backups_academic_year_id"), "timetable_backups", ["academic_year_id"], unique=False)
    op.create_index(op.f("ix_timetable_backups_timetable_id"), "timetable_backups", ["timetable_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_timetable_backups_timetable_id"), table_name="timetable_backups")
    op.drop_index(op.f("ix_timetable_backups_academic_year_id"), table_name="timetable_backups")
    op.drop_table("timetable_backups")
