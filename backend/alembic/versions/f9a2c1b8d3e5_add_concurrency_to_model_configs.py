"""add concurrency to model configs

Revision ID: f9a2c1b8d3e5
Revises: 40f830e2ff94
Create Date: 2025-11-25 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9a2c1b8d3e5'
down_revision: Union[str, None] = '40f830e2ff94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add concurrency column with default value of 3
    op.add_column('model_configs', sa.Column('concurrency', sa.Integer(), nullable=True))

    # Set default value for existing rows
    op.execute("UPDATE model_configs SET concurrency = 3 WHERE concurrency IS NULL")

    # Make it not nullable after setting defaults
    op.alter_column('model_configs', 'concurrency', nullable=False, server_default='3')


def downgrade():
    op.drop_column('model_configs', 'concurrency')
