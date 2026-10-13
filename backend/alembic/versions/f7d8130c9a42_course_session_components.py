"""course session components

Revision ID: f7d8130c9a42
Revises: d94e207f4c12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7d8130c9a42"
down_revision: Union[str, None] = "d94e207f4c12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("course_offerings") as batch_op:
        batch_op.add_column(sa.Column("theory_sessions_per_week", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("lecture_sessions_per_week", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("theory_faculty_ids", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("lecture_faculty_ids", sa.JSON(), nullable=False, server_default="[]"))
    op.execute("UPDATE course_offerings SET theory_sessions_per_week = sessions_per_week, theory_faculty_ids = faculty_ids WHERE kind <> 'lab'")
    with op.batch_alter_table("timetable_sessions") as batch_op:
        batch_op.add_column(sa.Column("session_type", sa.String(length=20), nullable=False, server_default="theory"))
    op.execute("UPDATE timetable_sessions SET session_type = 'lab' WHERE course_offering_id IN (SELECT id FROM course_offerings WHERE kind = 'lab')")


def downgrade() -> None:
    with op.batch_alter_table("timetable_sessions") as batch_op:
        batch_op.drop_column("session_type")
    with op.batch_alter_table("course_offerings") as batch_op:
        batch_op.drop_column("lecture_faculty_ids")
        batch_op.drop_column("theory_faculty_ids")
        batch_op.drop_column("lecture_sessions_per_week")
        batch_op.drop_column("theory_sessions_per_week")
