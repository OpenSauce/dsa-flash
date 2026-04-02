"""add coding problem tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "codingproblem",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("difficulty", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("tags", ARRAY(sa.String()), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("examples", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("starter_code", sa.JSON(), nullable=False),
        sa.Column("test_cases", sa.JSON(), nullable=False),
        sa.Column("solution", sa.JSON(), nullable=False),
        sa.Column("hints", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_codingproblem_category"),
        "codingproblem",
        ["category"],
        unique=False,
        if_not_exists=True,
    )

    op.create_table(
        "usercodingproblem",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("coding_problem_id", sa.Integer(), nullable=False),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interval", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("easiness", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("next_review", sa.DateTime(), nullable=True),
        sa.Column("last_reviewed", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["coding_problem_id"], ["codingproblem.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "coding_problem_id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_usercodingproblem_coding_problem_id",
        "usercodingproblem",
        ["coding_problem_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_usercodingproblem_coding_problem_id", table_name="usercodingproblem")
    op.drop_table("usercodingproblem")
    op.drop_index(op.f("ix_codingproblem_category"), table_name="codingproblem")
    op.drop_table("codingproblem")
