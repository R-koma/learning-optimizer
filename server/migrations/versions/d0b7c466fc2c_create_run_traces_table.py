"""create run_traces table

Revision ID: d0b7c466fc2c
Revises: 8c1f4a7b9e21
Create Date: 2026-04-27 13:50:58.200696

"""

from collections.abc import Sequence

from alembic import op

revision: str = "d0b7c466fc2c"
down_revision: str | Sequence[str] | None = "8c1f4a7b9e21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""--sql
        CREATE TABLE run_traces (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            dialogue_session_id  UUID NOT NULL REFERENCES dialogue_sessions(id) ON DELETE CASCADE,
            user_id              TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            trace_id             UUID NOT NULL,
            span_id              UUID NOT NULL,
            parent_span_id       UUID,
            event_type           TEXT NOT NULL CHECK (event_type IN ('node', 'llm')),
            node_name            TEXT,
            model_name           TEXT,
            status               TEXT NOT NULL CHECK (status IN ('success', 'failed')),
            started_at           TIMESTAMPTZ NOT NULL,
            ended_at             TIMESTAMPTZ NOT NULL,
            latency_ms           INTEGER NOT NULL,
            input_tokens         INTEGER,
            output_tokens        INTEGER,
            total_tokens         INTEGER,
            dialogue_turn_count  INTEGER,
            error_type           TEXT,
            error_message        TEXT,
            metadata             JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX idx_run_traces_session_id ON run_traces(dialogue_session_id)")
    op.execute("CREATE INDEX idx_run_traces_trace_id ON run_traces(trace_id)")
    op.execute("CREATE INDEX idx_run_traces_event_type ON run_traces(event_type)")
    op.execute("CREATE INDEX idx_run_traces_node_name ON run_traces(node_name)")
    op.execute("CREATE INDEX idx_run_traces_created_at ON run_traces(created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_run_traces_created_at")
    op.execute("DROP INDEX IF EXISTS idx_run_traces_node_name")
    op.execute("DROP INDEX IF EXISTS idx_run_traces_event_type")
    op.execute("DROP INDEX IF EXISTS idx_run_traces_trace_id")
    op.execute("DROP INDEX IF EXISTS idx_run_traces_session_id")
    op.execute("DROP TABLE IF EXISTS run_traces")
