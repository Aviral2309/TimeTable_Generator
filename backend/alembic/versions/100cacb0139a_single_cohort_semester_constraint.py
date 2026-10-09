"""single cohort semester constraint

Revision ID: 100cacb0139a
Revises: e02d1fb10af5
Create Date: 2026-10-09 18:26:29.561589
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '100cacb0139a'
down_revision: Union[str, None] = 'e02d1fb10af5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table('semester_offerings') as batch_op:
        batch_op.create_unique_constraint('uq_single_semester_cohort', ['academic_year_id', 'department_id', 'semester_number'])

def downgrade() -> None:
    with op.batch_alter_table('semester_offerings') as batch_op:
        batch_op.drop_constraint('uq_single_semester_cohort', type_='unique')

