"""add_evaluation_tables

Revision ID: 40f830e2ff94
Revises: 29312a5c2041
Create Date: 2025-11-23 23:09:43.332061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40f830e2ff94'
down_revision: Union[str, None] = '29312a5c2041'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create model_configs table
    op.create_table('model_configs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('additional_params', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create evaluations table
    op.create_table('evaluations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('dataset_id', sa.UUID(), nullable=False),
        sa.Column('model_config_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('total_images', sa.Integer(), nullable=True),
        sa.Column('processed_images', sa.Integer(), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('results_summary', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
        sa.ForeignKeyConstraint(['model_config_id'], ['model_configs.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create evaluation_results table
    op.create_table('evaluation_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('evaluation_id', sa.UUID(), nullable=False),
        sa.Column('image_id', sa.UUID(), nullable=False),
        sa.Column('model_response', sa.Text(), nullable=True),
        sa.Column('parsed_answer', sa.JSON(), nullable=True),
        sa.Column('ground_truth', sa.JSON(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.id'], ),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('evaluation_results')
    op.drop_table('evaluations')
    op.drop_table('model_configs')
