"""add_manually_edited_at_to_notes

Revision ID: c3f1a9e2d7b8
Revises: 37c71686bc3a
Create Date: 2026-06-06 14:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c3f1a9e2d7b8"
down_revision: str | Sequence[str] | None = "37c71686bc3a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ユーザーが手動編集した時刻。復習再生成（#235）が本文を侵食しないための来歴フラグとして使う
    op.execute("ALTER TABLE notes ADD COLUMN manually_edited_at TIMESTAMPTZ")


def downgrade() -> None:
    op.execute("ALTER TABLE notes DROP COLUMN IF EXISTS manually_edited_at")
