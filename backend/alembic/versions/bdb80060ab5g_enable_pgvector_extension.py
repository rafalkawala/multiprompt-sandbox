"""Enable pgvector extension

Revision ID: bdb80060ab5g
Revises: bdb80060ab5f
Create Date: 2024-05-23 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'bdb80060ab5g'
down_revision: Union[str, None] = 'bdb80060ab5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension for PostgreSQL
    # This extension provides the 'vector' data type for storing embeddings
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')


def downgrade() -> None:
    # Drop the extension (use CASCADE to handle dependencies)
    op.execute('DROP EXTENSION IF EXISTS vector CASCADE')
