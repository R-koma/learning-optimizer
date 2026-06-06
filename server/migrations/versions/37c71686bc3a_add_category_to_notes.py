"""add_category_to_notes

Revision ID: 37c71686bc3a
Revises: b8d2f4a16c37
Create Date: 2026-06-06 13:35:35.055698

"""

from collections.abc import Sequence

from alembic import op

revision: str = "37c71686bc3a"
down_revision: str | Sequence[str] | None = "b8d2f4a16c37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE notes ADD COLUMN category TEXT")
    op.execute("CREATE INDEX idx_notes_user_category ON notes(user_id, category)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_notes_user_category")
    op.execute("ALTER TABLE notes DROP COLUMN IF EXISTS category")
