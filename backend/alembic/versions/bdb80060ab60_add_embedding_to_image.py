"""Add embedding to image

Revision ID: bdb80060ab60
Revises: bdb80060ab5g
Create Date: 2024-05-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'bdb80060ab60'
down_revision: Union[str, None] = 'bdb80060ab5g'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add vector column for storing multimodal embeddings
    # Dimension 1408 is the default output dimension for multimodalembedding@001
    op.add_column('images', sa.Column('embedding', Vector(1408), nullable=True))


def downgrade() -> None:
    op.drop_column('images', 'embedding')
