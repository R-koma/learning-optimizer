"""add_unique_feedback_per_note

Revision ID: 8c1f4a7b9e21
Revises: 40d4592353e2
Create Date: 2026-04-25 22:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "8c1f4a7b9e21"
down_revision: str | Sequence[str] | None = "40d4592353e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""--sql
        DELETE FROM feedbacks f
        USING feedbacks f2
        WHERE f.note_id = f2.note_id
          AND (f.created_at < f2.created_at
               OR (f.created_at = f2.created_at AND f.id < f2.id))
    """)

    op.execute("ALTER TABLE feedbacks ADD CONSTRAINT feedbacks_note_id_key UNIQUE (note_id)")


def downgrade() -> None:
    op.execute("ALTER TABLE feedbacks DROP CONSTRAINT IF EXISTS feedbacks_note_id_key")
