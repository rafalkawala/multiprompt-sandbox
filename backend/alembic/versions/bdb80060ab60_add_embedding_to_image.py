"""Add embedding to image

Revision ID: bdb80060ab60
Revises: bdb80060ab5f
Create Date: 2024-05-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bdb80060ab60'
down_revision: Union[str, None] = 'bdb80060ab5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('images', sa.Column('embedding', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('images', 'embedding')
