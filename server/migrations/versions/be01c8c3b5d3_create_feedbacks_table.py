"""create_feedbacks_table

Revision ID: be01c8c3b5d3
Revises: 7fd4c2db4312
Create Date: 2026-03-11 14:26:55.028510

"""

from collections.abc import Sequence

from alembic import op

revision: str = "be01c8c3b5d3"
down_revision: str | Sequence[str] | None = "7fd4c2db4312"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""--sql
        CREATE TABLE feedbacks (
               id                   TEXT PRIMARY KEY,
               note_id              TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
               dialogue_session_id  TEXT REFERENCES dialogue_sessions(id),
               understanding_level  TEXT NOT NULL CHECK (understanding_level in ('high', 'medium', 'low')),
               strength             TEXT,
               improvements         TEXT,
               created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX idx_feedbacks_note_id ON feedbacks(note_id)")
    op.execute("CREATE INDEX idx_feedbacks_dialogue_session_id ON feedbacks(dialogue_session_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_feedbacks_note_id")
    op.execute("DROP INDEX IF EXISTS idx_feedbacks_dialogue_session_id")
    op.execute("DROP TABLE IF EXISTS feedbacks")
