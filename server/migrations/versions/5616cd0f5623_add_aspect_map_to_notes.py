"""add_aspect_map_to_notes

Revision ID: 5616cd0f5623
Revises: d0b7c466fc2c
Create Date: 2026-05-12 07:41:29.942058

"""

from collections.abc import Sequence

from alembic import op

revision: str = "5616cd0f5623"
down_revision: str | Sequence[str] | None = "d0b7c466fc2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE notes ADD COLUMN aspect_map JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE notes DROP COLUMN IF EXISTS aspect_map")
