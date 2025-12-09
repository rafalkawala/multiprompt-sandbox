"""add_cost_tracking_columns

Revision ID: 732f8c05a1e9
Revises: fcfbf17e4102
Create Date: 2025-12-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '732f8c05a1e9'
down_revision: Union[str, None] = 'fcfbf17e4102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Model Configs
    op.add_column('model_configs', sa.Column('pricing_config', sa.JSON(), nullable=True))

    # Evaluations
    op.add_column('evaluations', sa.Column('estimated_cost', sa.Float(), nullable=True))
    op.add_column('evaluations', sa.Column('actual_cost', sa.Float(), nullable=True))
    op.add_column('evaluations', sa.Column('cost_details', sa.JSON(), nullable=True))

    # Labelling Jobs
    op.add_column('labelling_jobs', sa.Column('total_cost', sa.Float(), nullable=True))
    op.add_column('labelling_job_runs', sa.Column('cost', sa.Float(), nullable=True))
    op.add_column('labelling_job_runs', sa.Column('cost_details', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Labelling Jobs
    op.drop_column('labelling_job_runs', 'cost_details')
    op.drop_column('labelling_job_runs', 'cost')
    op.drop_column('labelling_jobs', 'total_cost')

    # Evaluations
    op.drop_column('evaluations', 'cost_details')
    op.drop_column('evaluations', 'actual_cost')
    op.drop_column('evaluations', 'estimated_cost')

    # Model Configs
    op.drop_column('model_configs', 'pricing_config')
