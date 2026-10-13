"""resource availability notes

Revision ID: d94e207f4c12
Revises: c81f3a2d904b
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d94e207f4c12"
down_revision: Union[str, None] = "c81f3a2d904b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("faculty_availability") as batch_op:
        batch_op.add_column(sa.Column("note", sa.String(length=300), nullable=False, server_default=""))
    op.create_table(
        "room_availability",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.String(length=12), nullable=False),
        sa.Column("period_index", sa.Integer(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(length=300), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "day", "period_index"),
    )


def downgrade() -> None:
    op.drop_table("room_availability")
    with op.batch_alter_table("faculty_availability") as batch_op:
        batch_op.drop_column("note")
