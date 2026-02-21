"""add lesson_slug to flashcard

Revision ID: 0004
Revises: 0003
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("flashcard", sa.Column("lesson_slug", sa.String(), nullable=True))
    op.create_index(
        op.f("ix_flashcard_lesson_slug"), "flashcard", ["lesson_slug"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_flashcard_lesson_slug"), table_name="flashcard")
    op.drop_column("flashcard", "lesson_slug")
