"""add auth_type to model_config

Revision ID: add_auth_type
Revises: add_selection_config
Create Date: 2025-12-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_auth_type'
down_revision = '4817bfb92f7f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('model_configs', sa.Column('auth_type', sa.String(), server_default='api_key', nullable=False))


def downgrade() -> None:
    op.drop_column('model_configs', 'auth_type')
