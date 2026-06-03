"""add graph_version to dialogue_sessions

Revision ID: a7f3e9c1d2b4
Revises: 9a2e1f3c4b5d
Create Date: 2026-06-03 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "a7f3e9c1d2b4"
down_revision: str | Sequence[str] | None = "9a2e1f3c4b5d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 既存行は旧トポロジー世代として 1 を埋める（DEFAULT 1 でバックフィル）。
    # 新規行はアプリが現行世代を明示挿入するため、この DEFAULT には依存しない。
    op.execute("""--sql
        ALTER TABLE dialogue_sessions
        ADD COLUMN graph_version INTEGER NOT NULL DEFAULT 1
    """)


def downgrade() -> None:
    op.execute("""--sql
        ALTER TABLE dialogue_sessions
        DROP COLUMN graph_version
    """)
