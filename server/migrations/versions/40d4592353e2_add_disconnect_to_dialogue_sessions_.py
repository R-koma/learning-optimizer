"""add disconnect to dialogue_sessions status check

Revision ID: 40d4592353e2
Revises: c3c8c7691159
Create Date: 2026-03-21 01:37:25.260675

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "40d4592353e2"
down_revision: str | Sequence[str] | None = "c3c8c7691159"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""--sql
        ALTER TABLE dialogue_sessions
        DROP CONSTRAINT dialogue_sessions_status_check
    """)
    op.execute("""--sql
        ALTER TABLE dialogue_sessions
        ADD CONSTRAINT dialogue_sessions_status_check
        CHECK (status IN ('in_progress', 'generate_note', 'completed', 'failed', 'disconnect'))
    """)


def downgrade() -> None:
    op.execute("""--sql
        ALTER TABLE dialogue_sessions
        DROP CONSTRAINT dialogue_sessions_status_check
    """)
    op.execute("""--sql
        ALTER TABLE dialogue_sessions
        ADD CONSTRAINT dialogue_sessions_status_check
        CHECK (status IN ('in_progress', 'generate_note', 'completed', 'failed'))
    """)
