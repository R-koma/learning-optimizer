"""add status to dialogue_sessions

Revision ID: c3c8c7691159
Revises: 184053fa5cf9
Create Date: 2026-03-14 14:31:14.658049

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c3c8c7691159"
down_revision: str | Sequence[str] | None = "184053fa5cf9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""--sql
        ALTER TABLE dialogue_sessions
        ADD COLUMN status TEXT NOT NULL DEFAULT 'in_progress'
        CHECK (status IN ('in_progress', 'generate_note', 'completed', 'failed'))
    """)


def downgrade() -> None:
    op.execute("""--sql
               ALTER TABLE dialogue_sessions
               DROP COLUMN status;
               """)
