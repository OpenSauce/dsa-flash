"""add ON DELETE to user FK constraints

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # userflashcard.user_id: add ON DELETE CASCADE
    op.drop_constraint("userflashcard_user_id_fkey", "userflashcard", type_="foreignkey")
    op.create_foreign_key(
        "userflashcard_user_id_fkey",
        "userflashcard",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # studysession.user_id: add ON DELETE CASCADE
    op.drop_constraint("studysession_user_id_fkey", "studysession", type_="foreignkey")
    op.create_foreign_key(
        "studysession_user_id_fkey",
        "studysession",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # event.user_id: add ON DELETE SET NULL
    op.drop_constraint("event_user_id_fkey", "event", type_="foreignkey")
    op.create_foreign_key(
        "event_user_id_fkey",
        "event",
        "user",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Revert event.user_id to plain FK (no ON DELETE)
    op.drop_constraint("event_user_id_fkey", "event", type_="foreignkey")
    op.create_foreign_key(
        "event_user_id_fkey",
        "event",
        "user",
        ["user_id"],
        ["id"],
    )

    # Revert studysession.user_id to plain FK (no ON DELETE)
    op.drop_constraint("studysession_user_id_fkey", "studysession", type_="foreignkey")
    op.create_foreign_key(
        "studysession_user_id_fkey",
        "studysession",
        "user",
        ["user_id"],
        ["id"],
    )

    # Revert userflashcard.user_id to plain FK (no ON DELETE)
    op.drop_constraint("userflashcard_user_id_fkey", "userflashcard", type_="foreignkey")
    op.create_foreign_key(
        "userflashcard_user_id_fkey",
        "userflashcard",
        "user",
        ["user_id"],
        ["id"],
    )
