"""add quiz, quizquestion, and userquizattempt tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quiz",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("lesson_slug", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_quiz_slug"), "quiz", ["slug"], unique=True, if_not_exists=True
    )
    op.create_index(
        op.f("ix_quiz_category"), "quiz", ["category"], unique=False, if_not_exists=True
    )
    op.create_index(
        op.f("ix_quiz_lesson_slug"), "quiz", ["lesson_slug"], unique=False, if_not_exists=True
    )

    op.create_table(
        "quizquestion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quiz_id", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("correct_index", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["quiz_id"], ["quiz.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_quizquestion_quiz_id"), "quizquestion", ["quiz_id"], unique=False, if_not_exists=True
    )

    op.create_table(
        "userquizattempt",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("quiz_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quiz_id"], ["quiz.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "quiz_id", name="uq_userquizattempt_user_quiz"),
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_userquizattempt_user_id"), "userquizattempt", ["user_id"], unique=False, if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_userquizattempt_user_id"), table_name="userquizattempt")
    op.drop_table("userquizattempt")
    op.drop_index(op.f("ix_quizquestion_quiz_id"), table_name="quizquestion")
    op.drop_table("quizquestion")
    op.drop_index(op.f("ix_quiz_lesson_slug"), table_name="quiz")
    op.drop_index(op.f("ix_quiz_category"), table_name="quiz")
    op.drop_index(op.f("ix_quiz_slug"), table_name="quiz")
    op.drop_table("quiz")
