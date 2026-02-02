"""merge_multiple_heads_2

Revision ID: 955cacccf8ec
Revises: 8aadcf9dbee3, abc06ba8c715
Create Date: 2026-02-02 01:57:58.021268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '955cacccf8ec'
down_revision: Union[str, Sequence[str], None] = ('8aadcf9dbee3', 'abc06ba8c715')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
