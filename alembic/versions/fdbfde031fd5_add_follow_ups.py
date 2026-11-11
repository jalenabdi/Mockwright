"""add follow-ups

Revision ID: fdbfde031fd5
Revises: 29730d21b4d6
Create Date: 2026-11-11 14:00:40.892572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdbfde031fd5'
down_revision: Union[str, Sequence[str], None] = '29730d21b4d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('follow_ups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('interview_question_id', sa.Integer(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('question_text', sa.Text(), nullable=False),
    sa.Column('answer_text', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint('position >= 1', name='ck_follow_ups_position_positive'),
    sa.ForeignKeyConstraint(['interview_question_id'], ['interview_questions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('interview_question_id', 'position', name='uq_follow_ups_interview_question_id_position')
    )
    op.create_index(op.f('ix_follow_ups_interview_question_id'), 'follow_ups', ['interview_question_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_follow_ups_interview_question_id'), table_name='follow_ups')
    op.drop_table('follow_ups')
