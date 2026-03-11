"""create_review_schedules_table

Revision ID: cc4e8454ad40
Revises: be01c8c3b5d3
Create Date: 2026-03-11 14:46:28.613552

"""

from collections.abc import Sequence

from alembic import op

revision: str = "cc4e8454ad40"
down_revision: str | Sequence[str] | None = "be01c8c3b5d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""--sql
        CREATE TABLE review_schedules (
            id                  TEXT PRIMARY KEY,
            note_id             TEXT NOT NULL REFERENCES notes(id),
            review_count        INTEGER NOT NULL DEFAULT 0,
            next_review_at      TIMESTAMPTZ NOT NULL,
            last_reviewed_at    TIMESTAMPTZ,
            status              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN('pending', 'completed', 'overdue')),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX idx_review_schedules_note_id ON review_schedules(note_id)")
    op.execute("CREATE INDEX idx_review_schedules_status ON review_schedules(note_id, status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_review_schedules_status")
    op.excute("DROP INDEX IF EXISTS idx_review_schedules_note_id")
    op.execute("DROP TABLE IF EXISTS review_schedules")
