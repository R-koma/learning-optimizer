"""change_app_table_id_columns_to_uuid

Revision ID: 184053fa5cf9
Revises: cc4e8454ad40
Create Date: 2026-03-14 11:15:48.986980

"""

from collections.abc import Sequence

from alembic import op

revision: str = "184053fa5cf9"
down_revision: str | Sequence[str] | None = "cc4e8454ad40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE dialogue_sessions DROP CONSTRAINT dialogue_sessions_note_id_fkey")
    op.execute("ALTER TABLE dialogue_messages DROP CONSTRAINT dialogue_messages_dialogue_session_id_fkey")
    op.execute("ALTER TABLE feedbacks DROP CONSTRAINT feedbacks_note_id_fkey")
    op.execute("ALTER TABLE feedbacks DROP CONSTRAINT feedbacks_dialogue_session_id_fkey")
    op.execute("ALTER TABLE review_schedules DROP CONSTRAINT review_schedules_note_id_fkey")

    op.execute("ALTER TABLE notes ALTER COLUMN id TYPE UUID USING id::UUID")
    op.execute("ALTER TABLE dialogue_sessions ALTER COLUMN id TYPE UUID USING id::UUID")
    op.execute("ALTER TABLE dialogue_sessions ALTER COLUMN note_id TYPE UUID USING note_id::UUID")
    op.execute("ALTER TABLE dialogue_messages ALTER COLUMN id TYPE UUID USING id::UUID")
    op.execute(
        "ALTER TABLE dialogue_messages ALTER COLUMN dialogue_session_id TYPE UUID USING dialogue_session_id::UUID"
    )
    op.execute("ALTER TABLE feedbacks ALTER COLUMN id TYPE UUID USING id::UUID")
    op.execute("ALTER TABLE feedbacks ALTER COLUMN note_id TYPE UUID USING note_id::UUID")
    op.execute("ALTER TABLE feedbacks ALTER COLUMN dialogue_session_id TYPE UUID USING dialogue_session_id::UUID")
    op.execute("ALTER TABLE review_schedules ALTER COLUMN id TYPE UUID USING id::UUID")
    op.execute("ALTER TABLE review_schedules ALTER COLUMN note_id TYPE UUID USING note_id::UUID")

    op.execute("""
        ALTER TABLE dialogue_sessions
        ADD CONSTRAINT dialogue_sessions_note_id_fkey
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE SET NULL
    """)
    op.execute("""
        ALTER TABLE dialogue_messages
        ADD CONSTRAINT dialogue_messages_dialogue_session_id_fkey
        FOREIGN KEY (dialogue_session_id) REFERENCES dialogue_sessions(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE feedbacks
        ADD CONSTRAINT feedbacks_note_id_fkey
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE feedbacks
        ADD CONSTRAINT feedbacks_dialogue_session_id_fkey
        FOREIGN KEY (dialogue_session_id) REFERENCES dialogue_sessions(id)
    """)
    op.execute("""
        ALTER TABLE review_schedules
        ADD CONSTRAINT review_schedules_note_id_fkey
        FOREIGN KEY (note_id) REFERENCES notes(id)
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE dialogue_sessions DROP CONSTRAINT dialogue_sessions_note_id_fkey")
    op.execute("ALTER TABLE dialogue_messages DROP CONSTRAINT dialogue_messages_dialogue_session_id_fkey")
    op.execute("ALTER TABLE feedbacks DROP CONSTRAINT feedbacks_note_id_fkey")
    op.execute("ALTER TABLE feedbacks DROP CONSTRAINT feedbacks_dialogue_session_id_fkey")
    op.execute("ALTER TABLE review_schedules DROP CONSTRAINT review_schedules_note_id_fkey")

    op.execute("ALTER TABLE notes ALTER COLUMN id TYPE TEXT USING id::TEXT")
    op.execute("ALTER TABLE dialogue_sessions ALTER COLUMN id TYPE TEXT USING id::TEXT")
    op.execute("ALTER TABLE dialogue_sessions ALTER COLUMN note_id TYPE TEXT USING note_id::TEXT")
    op.execute("ALTER TABLE dialogue_messages ALTER COLUMN id TYPE TEXT USING id::TEXT")
    op.execute(
        "ALTER TABLE dialogue_messages ALTER COLUMN dialogue_session_id TYPE TEXT USING dialogue_session_id::TEXT"
    )
    op.execute("ALTER TABLE feedbacks ALTER COLUMN id TYPE TEXT USING id::TEXT")
    op.execute("ALTER TABLE feedbacks ALTER COLUMN note_id TYPE TEXT USING note_id::TEXT")
    op.execute("ALTER TABLE feedbacks ALTER COLUMN dialogue_session_id TYPE TEXT USING dialogue_session_id::TEXT")
    op.execute("ALTER TABLE review_schedules ALTER COLUMN id TYPE TEXT USING id::TEXT")
    op.execute("ALTER TABLE review_schedules ALTER COLUMN note_id TYPE TEXT USING note_id::TEXT")

    op.execute("""
        ALTER TABLE dialogue_sessions
        ADD CONSTRAINT dialogue_sessions_note_id_fkey
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE SET NULL
    """)
    op.execute("""
        ALTER TABLE dialogue_messages
        ADD CONSTRAINT dialogue_messages_dialogue_session_id_fkey
        FOREIGN KEY (dialogue_session_id) REFERENCES dialogue_sessions(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE feedbacks
        ADD CONSTRAINT feedbacks_note_id_fkey
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE feedbacks
        ADD CONSTRAINT feedbacks_dialogue_session_id_fkey
        FOREIGN KEY (dialogue_session_id) REFERENCES dialogue_sessions(id)
    """)
    op.execute("""
        ALTER TABLE review_schedules
        ADD CONSTRAINT review_schedules_note_id_fkey
        FOREIGN KEY (note_id) REFERENCES notes(id)
    """)
