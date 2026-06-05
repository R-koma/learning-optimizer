"""create_dialogue_message_images_table

Revision ID: b8d2f4a16c37
Revises: a7f3e9c1d2b4
Create Date: 2026-06-05 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b8d2f4a16c37"
down_revision: str | Sequence[str] | None = "a7f3e9c1d2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 画像バイナリ自体はオブジェクトストレージに置き、ここには参照（storage_key）と
    # メタのみ保持する。メッセージ削除時にカスケードで掃除する。
    op.execute("""--sql
        CREATE TABLE dialogue_message_images (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            dialogue_message_id UUID NOT NULL REFERENCES dialogue_messages(id) ON DELETE CASCADE,
            storage_key         TEXT NOT NULL,
            mime_type           TEXT NOT NULL,
            image_order         INTEGER NOT NULL,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_dialogue_message_images_message_id ON dialogue_message_images(dialogue_message_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_dialogue_message_images_message_id")
    op.execute("DROP TABLE IF EXISTS dialogue_message_images")
