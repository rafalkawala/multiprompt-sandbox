"""merge heads

Revision ID: b711e2d14ebe
Revises: 20260114110001, bdb80060ab60
Create Date: 2026-01-14 11:20:29.140354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b711e2d14ebe'
down_revision: Union[str, None] = ('20260114110001', 'bdb80060ab60')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
