"""create_dialogue_messages_table

Revision ID: 7fd4c2db4312
Revises: ac5b54e9b904
Create Date: 2026-03-11 14:03:20.001525

"""

from collections.abc import Sequence

from alembic import op

revision: str = "7fd4c2db4312"
down_revision: str | Sequence[str] | None = "ac5b54e9b904"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""--sql
        CREATE TABLE dialogue_messages (
                id TEXT PRIMARY KEY,
                dialogue_session_id TEXT NOT NULL REFERENCES         dialogue_session(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                message_order INTEGER NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX idx_dialogue_messages_dialogue_session_id ON dialogue_messages(dialogue_session_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_dialogue_messages_dialogue_session_id")
    op.execute("DROP TABLE IF EXISTS dialogue_messages")
