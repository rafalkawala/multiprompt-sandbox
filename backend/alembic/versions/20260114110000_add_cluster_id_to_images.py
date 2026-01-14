"""Add cluster_id to images for k-means clustering

Revision ID: 20260114110000
Revises: 8b1234567890
Create Date: 2026-01-14 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260114110000'
down_revision: Union[str, None] = '8b1234567890'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add cluster_id for k-means cluster assignment
    op.add_column('images', sa.Column('cluster_id', sa.Integer(), nullable=True))

    # Add index for faster cluster-based queries
    op.create_index('idx_images_cluster_id', 'images', ['cluster_id'])


def downgrade() -> None:
    op.drop_index('idx_images_cluster_id', table_name='images')
    op.drop_column('images', 'cluster_id')
