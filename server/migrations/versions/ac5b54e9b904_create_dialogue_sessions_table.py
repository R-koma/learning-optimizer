"""create_dialogue_sessions_table

Revision ID: ac5b54e9b904
Revises: eadeed865551
Create Date: 2026-03-11 13:42:43.356676

"""

from collections.abc import Sequence

from alembic import op

revision: str = "ac5b54e9b904"
down_revision: str | Sequence[str] | None = "eadeed865551"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""--sql
        CREATE TABLE dialogue_sessions(
               id TEXT PRIMARY KEY,
               user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
               note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE SET NULL,
               session_type TEXT NOT NULL CHECK(session_type IN ('learning', 'review')),
               langgraph_thread_id TEXT,
               started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
               ended_at TIMESTAMPTZ

        )
    """)

    op.execute("CREATE INDEX idx_dialogue_session_user_id ON dialogue_sessions(user_id)")
    op.execute("CREATE INDEX idx_dialogue_session_note_id ON dialogue_sessions(note_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_dialogue_session_note_id")
    op.execute("DROP INDEX IF EXISTS idx_dialogue_session_user_id")
    op.execute("DROP TABLE IF EXISTS dialogue_sessions")
