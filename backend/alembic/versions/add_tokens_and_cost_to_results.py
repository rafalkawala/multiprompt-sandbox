"""add tokens and cost to results

Revision ID: add_tokens_cost
Revises: add_auth_type
Create Date: 2025-12-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_tokens_cost'
down_revision = 'add_auth_type'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('evaluation_results', sa.Column('prompt_tokens', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('evaluation_results', sa.Column('completion_tokens', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('evaluation_results', sa.Column('cost', sa.Float(), nullable=True, server_default='0.0'))


def downgrade() -> None:
    op.drop_column('evaluation_results', 'cost')
    op.drop_column('evaluation_results', 'completion_tokens')
    op.drop_column('evaluation_results', 'prompt_tokens')
