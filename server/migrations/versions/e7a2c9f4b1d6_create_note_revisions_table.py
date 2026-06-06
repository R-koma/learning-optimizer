"""create_note_revisions_table

Revision ID: e7a2c9f4b1d6
Revises: c3f1a9e2d7b8
Create Date: 2026-06-06 15:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "e7a2c9f4b1d6"
down_revision: str | Sequence[str] | None = "c3f1a9e2d7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 手動編集済みノートの復習で生成される AI 追記（アデンダ）を append-only で保持する。
    # base 本文（notes.content）は書き換えず、表示時に base + revisions を合成する（#235）
    op.execute("""--sql
        CREATE TABLE note_revisions (
               id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
               note_id              UUID NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
               dialogue_session_id  UUID REFERENCES dialogue_sessions(id),
               content              TEXT NOT NULL,
               created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_note_revisions_note_id ON note_revisions(note_id, created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_note_revisions_note_id")
    op.execute("DROP TABLE IF EXISTS note_revisions")
