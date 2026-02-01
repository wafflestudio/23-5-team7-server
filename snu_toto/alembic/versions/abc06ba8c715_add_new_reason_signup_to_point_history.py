"""add new reason(signup) to point_history

Revision ID: abc06ba8c715
Revises: a458d5af1137
Create Date: 2026-02-01 22:51:24.548403

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abc06ba8c715'
down_revision: Union[str, Sequence[str], None] = 'a458d5af1137'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column('point_history', 'reason',
               existing_type=sa.Enum('BET', 'WIN', 'LOSE', 'REFUND', 'ETC', name='pointreason'),
               type_=sa.Enum('BET', 'WIN', 'LOSE', 'REFUND', 'ETC', 'SIGNUP', name='pointreason'),
               existing_nullable=False)

def downgrade():
    op.alter_column('point_history', 'reason',
               existing_type=sa.Enum('BET', 'WIN', 'LOSE', 'REFUND', 'ETC', 'SIGNUP', name='pointreason'),
               type_=sa.Enum('BET', 'WIN', 'LOSE', 'REFUND', 'ETC', name='pointreason'),
               existing_nullable=False)
