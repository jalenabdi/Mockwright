"""create interview_questions and answers

Revision ID: beff352812c6
Revises: 
Create Date: 2026-10-05 15:00:04.559532

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'beff352812c6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("interview_id", sa.Integer(), nullable=False),
        sa.Column("question_order", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "interview_id",
            "question_order",
            name="uq_interview_questions_interview_id_question_order",
        ),
        sa.CheckConstraint(
            "question_order >= 1",
            name="ck_interview_questions_question_order_positive",
        ),
    )
    op.create_index(
        "ix_interview_questions_interview_id",
        "interview_questions",
        ["interview_id"],
        unique=False,
    )

    op.create_table(
        "answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("interview_question_id", sa.Integer(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["interview_question_id"],
            ["interview_questions.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "interview_question_id",
            name="uq_answers_interview_question_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("answers")
    op.drop_index(
        "ix_interview_questions_interview_id",
        table_name="interview_questions",
    )
    op.drop_table("interview_questions")
