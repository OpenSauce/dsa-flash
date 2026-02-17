"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-02-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "flashcard",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("front", sa.String(), nullable=False),
        sa.Column("back", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("difficulty", sa.String(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_user_username"), "user", ["username"], unique=True, if_not_exists=True
    )
    op.create_table(
        "userflashcard",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("flashcard_id", sa.Integer(), nullable=False),
        sa.Column("repetitions", sa.Integer(), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False),
        sa.Column("easiness", sa.Float(), nullable=False),
        sa.Column("next_review", sa.DateTime(), nullable=True),
        sa.Column("last_reviewed", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["flashcard_id"], ["flashcard.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("user_id", "flashcard_id"),
        if_not_exists=True,
    )
    op.create_table(
        "event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_event_created_at"), "event", ["created_at"], unique=False, if_not_exists=True
    )
    op.create_index(
        op.f("ix_event_event_type"), "event", ["event_type"], unique=False, if_not_exists=True
    )
    op.create_index(
        op.f("ix_event_session_id"), "event", ["session_id"], unique=False, if_not_exists=True
    )
    op.create_table(
        "studysession",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("study_date", sa.Date(), nullable=False),
        sa.Column("cards_reviewed", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "study_date", name="uq_studysession_user_date"),
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_studysession_user_id"), "studysession", ["user_id"], unique=False, if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_studysession_user_id"), table_name="studysession")
    op.drop_table("studysession")
    op.drop_index(op.f("ix_event_session_id"), table_name="event")
    op.drop_index(op.f("ix_event_event_type"), table_name="event")
    op.drop_index(op.f("ix_event_created_at"), table_name="event")
    op.drop_table("event")
    op.drop_table("userflashcard")
    op.drop_index(op.f("ix_user_username"), table_name="user")
    op.drop_table("user")
    op.drop_table("flashcard")
