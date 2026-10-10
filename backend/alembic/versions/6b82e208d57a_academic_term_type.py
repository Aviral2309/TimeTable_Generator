"""academic term type

Revision ID: 6b82e208d57a
Revises: 100cacb0139a
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "6b82e208d57a"
down_revision: Union[str, None] = "100cacb0139a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("academic_years") as batch_op:
        batch_op.add_column(sa.Column("term_type", sa.String(length=10), nullable=False, server_default="odd"))


def downgrade() -> None:
    with op.batch_alter_table("academic_years") as batch_op:
        batch_op.drop_column("term_type")
