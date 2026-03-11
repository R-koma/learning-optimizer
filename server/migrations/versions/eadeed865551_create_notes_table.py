"""create_notes_table

Revision ID: eadeed865551
Revises: baf7e964d087
Create Date: 2026-03-11 01:24:21.753617

"""

from collections.abc import Sequence

from alembic import op

revision: str = "eadeed865551"
down_revision: str | Sequence[str] | None = "baf7e964d087"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""--sql
        CREATE TABLE notes(
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            topic       TEXT NOT NULL,
            content     TEXT NOT NULL,
            summary     TEXT,
            status      TEXT NOT NULL DEFAULT 'active' CHECK(status IN('active', 'archived')),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOT()
        )
    """)
    op.execute("CREATE INDEX idx_notes_user_id ON notes(user_id)")
    op.execute("CREATE INDEX idx_notes_status ON notes(user_id, status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_notes_status")
    op.execute("DROP INDEX IF EXISTS idx_notes_user_id")
    op.execute("DROP TABLE IF EXISTS notes")
