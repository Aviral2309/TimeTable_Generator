"""link student accounts to an academic year

Revision ID: a4e8f6c1d209
Revises: b1a34c7e908d
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4e8f6c1d209"
down_revision: Union[str, None] = "b1a34c7e908d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("academic_year_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_users_academic_year_id", "academic_years", ["academic_year_id"], ["id"])
        batch.create_index("ix_users_academic_year_id", ["academic_year_id"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_academic_year_id")
        batch.drop_constraint("fk_users_academic_year_id", type_="foreignkey")
        batch.drop_column("academic_year_id")
