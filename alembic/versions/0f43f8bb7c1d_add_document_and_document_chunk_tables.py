"""add document and document_chunk tables

Revision ID: 0f43f8bb7c1d
Revises: b614378dcd87
Create Date: 2026-08-29 03:59:41.785033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '0f43f8bb7c1d'
down_revision: Union[str, Sequence[str], None] = 'b614378dcd87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.create_table('documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=True),
    sa.Column('file_type', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('document_chunks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('chunk_text', sa.Text(), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('embedding', Vector(384), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('document_chunks')
    op.drop_table('documents')
