"""merge multiple heads

Revision ID: a458d5af1137
Revises: 6f029410fbd8, 9a9774779351
Create Date: 2026-01-31 13:59:40.853702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a458d5af1137'
down_revision: Union[str, Sequence[str], None] = ('6f029410fbd8', '9a9774779351')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
