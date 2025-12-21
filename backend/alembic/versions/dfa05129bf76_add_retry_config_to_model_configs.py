"""add_retry_config_to_model_configs

Revision ID: dfa05129bf76
Revises: add_tokens_cost
Create Date: 2025-12-16 17:20:22.461785

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dfa05129bf76'
down_revision: Union[str, None] = 'add_tokens_cost'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add retry_config column to model_configs table
    op.add_column('model_configs', sa.Column('retry_config', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove retry_config column from model_configs table
    op.drop_column('model_configs', 'retry_config')
