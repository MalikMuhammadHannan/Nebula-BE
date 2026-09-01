"""add embedding to blogs

Revision ID: e0e93b456ca7
Revises: 0f43f8bb7c1d
Create Date: 2026-09-01 04:23:01.832222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'e0e93b456ca7'
down_revision: Union[str, Sequence[str], None] = '0f43f8bb7c1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('blogs', sa.Column('embedding', Vector(384), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('blogs', 'embedding')
