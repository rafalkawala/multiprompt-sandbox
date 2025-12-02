"""add_labelling_jobs_tables

Revision ID: 4e8b5c417f8f
Revises: 640889d5a1e8
Create Date: 2025-12-02 16:22:46.017702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e8b5c417f8f'
down_revision: Union[str, None] = '640889d5a1e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create labelling_jobs table
    op.create_table('labelling_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('dataset_id', sa.UUID(), nullable=True),
        sa.Column('gcs_folder_path', sa.String(length=512), nullable=False),
        sa.Column('last_processed_timestamp', sa.DateTime(), nullable=True),
        sa.Column('model_config_id', sa.UUID(), nullable=False),
        sa.Column('system_message', sa.Text(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('frequency_minutes', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='idle'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('total_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_images_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_images_labeled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_errors', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['model_config_id'], ['model_configs.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create labelling_job_runs table
    op.create_table('labelling_job_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('labelling_job_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='running'),
        sa.Column('trigger_type', sa.String(length=50), nullable=False),
        sa.Column('images_discovered', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('images_ingested', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('images_labeled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('images_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['labelling_job_id'], ['labelling_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create labelling_results table
    op.create_table('labelling_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('labelling_job_id', sa.UUID(), nullable=False),
        sa.Column('labelling_job_run_id', sa.UUID(), nullable=False),
        sa.Column('image_id', sa.UUID(), nullable=False),
        sa.Column('model_response', sa.Text(), nullable=False),
        sa.Column('parsed_answer', sa.JSON(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('gcs_source_path', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['labelling_job_id'], ['labelling_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['labelling_job_run_id'], ['labelling_job_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('labelling_job_id', 'image_id', name='unique_job_image')
    )

    # Create indexes for better query performance
    op.create_index('idx_labelling_results_job', 'labelling_results', ['labelling_job_id'])
    op.create_index('idx_labelling_results_image', 'labelling_results', ['image_id'])
    op.create_index('idx_labelling_job_runs_job', 'labelling_job_runs', ['labelling_job_id'])


def downgrade() -> None:
    op.drop_index('idx_labelling_job_runs_job', table_name='labelling_job_runs')
    op.drop_index('idx_labelling_results_image', table_name='labelling_results')
    op.drop_index('idx_labelling_results_job', table_name='labelling_results')
    op.drop_table('labelling_results')
    op.drop_table('labelling_job_runs')
    op.drop_table('labelling_jobs')
