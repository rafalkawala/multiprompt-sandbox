"""add_performance_indexes

Revision ID: 36f3dd453206
Revises: dfa05129bf76
Create Date: 2025-12-16 21:53:17.652754

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36f3dd453206'
down_revision: Union[str, None] = 'dfa05129bf76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Projects - improve list sorting and ownership checks
    op.create_index('idx_projects_created_at', 'projects', [sa.text('created_at DESC')])
    op.create_index('idx_projects_created_by_id', 'projects', ['created_by_id'])

    # Datasets - optimize project-scoped queries
    op.create_index('idx_datasets_project_id', 'datasets', ['project_id'])
    op.create_index('idx_datasets_created_by_id', 'datasets', ['created_by_id'])

    # Images - improve pagination, duplicate detection, and status filtering
    op.create_index('idx_images_dataset_id_uploaded_at', 'images', ['dataset_id', sa.text('uploaded_at DESC')])
    op.create_index('idx_images_dataset_id_filename', 'images', ['dataset_id', 'filename'])
    op.create_index('idx_images_dataset_processing_status', 'images', ['dataset_id', 'processing_status'])

    # Evaluations - optimize user-scoped listing
    op.create_index('idx_evaluations_created_by_id_created_at', 'evaluations', ['created_by_id', sa.text('created_at DESC')])
    op.create_index('idx_evaluations_project_id', 'evaluations', ['project_id'])

    # Evaluation Results - improve result retrieval and filtering
    op.create_index('idx_evaluation_results_evaluation_id', 'evaluation_results', ['evaluation_id'])
    op.create_index('idx_evaluation_results_evaluation_id_is_correct', 'evaluation_results', ['evaluation_id', 'is_correct'])


def downgrade() -> None:
    # Remove indexes in reverse order
    op.drop_index('idx_evaluation_results_evaluation_id_is_correct', 'evaluation_results')
    op.drop_index('idx_evaluation_results_evaluation_id', 'evaluation_results')

    op.drop_index('idx_evaluations_project_id', 'evaluations')
    op.drop_index('idx_evaluations_created_by_id_created_at', 'evaluations')

    op.drop_index('idx_images_dataset_processing_status', 'images')
    op.drop_index('idx_images_dataset_id_filename', 'images')
    op.drop_index('idx_images_dataset_id_uploaded_at', 'images')

    op.drop_index('idx_datasets_created_by_id', 'datasets')
    op.drop_index('idx_datasets_project_id', 'datasets')

    op.drop_index('idx_projects_created_by_id', 'projects')
    op.drop_index('idx_projects_created_at', 'projects')
