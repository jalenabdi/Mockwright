"""create feedbacks table

Revision ID: 3673750eacfc
Revises: 3250151de418
Create Date: 2026-10-27 13:53:59.306482

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3673750eacfc'
down_revision: Union[str, Sequence[str], None] = '3250151de418'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    op.create_table(
        "feedbacks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "interview_id",
            sa.Integer(),
            sa.ForeignKey("interviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relevance_score", sa.Integer(), nullable=False),
        sa.Column("star_structure_score", sa.Integer(), nullable=False),
        sa.Column("specificity_score", sa.Integer(), nullable=False),
        sa.Column("individual_contribution_score", sa.Integer(), nullable=False),
        sa.Column("communication_score", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("strengths", postgresql.JSONB(), nullable=False),
        sa.Column("improvements", postgresql.JSONB(), nullable=False),
        sa.Column("next_step", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("interview_id", name="uq_feedbacks_interview_id"),
        sa.CheckConstraint("relevance_score BETWEEN 0 AND 20", name="ck_feedbacks_relevance_score_range"),
        sa.CheckConstraint("star_structure_score BETWEEN 0 AND 20", name="ck_feedbacks_star_structure_score_range"),
        sa.CheckConstraint("specificity_score BETWEEN 0 AND 20", name="ck_feedbacks_specificity_score_range"),
        sa.CheckConstraint(
            "individual_contribution_score BETWEEN 0 AND 20",
            name="ck_feedbacks_individual_contribution_score_range",
        ),
        sa.CheckConstraint("communication_score BETWEEN 0 AND 20", name="ck_feedbacks_communication_score_range"),
        sa.CheckConstraint("total_score BETWEEN 0 AND 100", name="ck_feedbacks_total_score_range"),
        sa.CheckConstraint(
            "total_score = relevance_score + star_structure_score + specificity_score"
            " + individual_contribution_score + communication_score",
            name="ck_feedbacks_total_score_sum",
        ),
    )


def downgrade() -> None:
    op.drop_table("feedbacks")
