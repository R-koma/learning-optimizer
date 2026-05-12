"""add abandoned to dialogue_sessions status check

Revision ID: 9a2e1f3c4b5d
Revises: 5616cd0f5623
Create Date: 2026-05-12 09:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "9a2e1f3c4b5d"
down_revision: str | Sequence[str] | None = "5616cd0f5623"
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
        CHECK (status IN ('in_progress', 'generate_note', 'completed', 'failed', 'disconnect', 'abandoned'))
    """)


def downgrade() -> None:
    op.execute("""--sql
        UPDATE dialogue_sessions SET status = 'failed' WHERE status = 'abandoned'
    """)
    op.execute("""--sql
        ALTER TABLE dialogue_sessions
        DROP CONSTRAINT dialogue_sessions_status_check
    """)
    op.execute("""--sql
        ALTER TABLE dialogue_sessions
        ADD CONSTRAINT dialogue_sessions_status_check
        CHECK (status IN ('in_progress', 'generate_note', 'completed', 'failed', 'disconnect'))
    """)
