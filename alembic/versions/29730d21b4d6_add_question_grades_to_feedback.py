"""add question grades to feedback

Revision ID: 29730d21b4d6
Revises: ad09c816e163
Create Date: 2026-11-11 10:13:00.781182

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '29730d21b4d6'
down_revision: Union[str, Sequence[str], None] = 'ad09c816e163'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('feedbacks', sa.Column('question_grades', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), server_default=sa.text("'[]'"), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('feedbacks', 'question_grades')
