"""
Add selection_config to evaluations table

Revision ID: add_selection_config
Revises: fcfbf17e4102
Create Date: 2025-12-08 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_selection_config'
down_revision: Union[str, None] = 'fcfbf17e4102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('evaluations', sa.Column('selection_config', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('evaluations', 'selection_config')
