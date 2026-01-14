"""Add purpose field to dataset_splits

Revision ID: 20260114110001
Revises: 20260114110000
Create Date: 2026-01-14 11:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260114110001'
down_revision: Union[str, None] = '20260114110000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add purpose field to distinguish split types
    op.add_column('dataset_splits', sa.Column('purpose', sa.String(), server_default='annotation', nullable=False))

    # Add index for purpose-based queries
    op.create_index('idx_dataset_splits_purpose', 'dataset_splits', ['purpose'])


def downgrade() -> None:
    op.drop_index('idx_dataset_splits_purpose', table_name='dataset_splits')
    op.drop_column('dataset_splits', 'purpose')
