"""add lesson and userlesson tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lesson",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("reading_time_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_lesson_slug"), "lesson", ["slug"], unique=True, if_not_exists=True
    )
    op.create_index(
        op.f("ix_lesson_category"), "lesson", ["category"], unique=False, if_not_exists=True
    )

    op.create_table(
        "userlesson",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lesson.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_userlesson_user_lesson"),
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_userlesson_user_id"), "userlesson", ["user_id"], unique=False, if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_userlesson_user_id"), table_name="userlesson")
    op.drop_table("userlesson")
    op.drop_index(op.f("ix_lesson_category"), table_name="lesson")
    op.drop_index(op.f("ix_lesson_slug"), table_name="lesson")
    op.drop_table("lesson")
