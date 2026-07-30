import uuid

import pytest

from core import config as app_config
from graph.version import GRAPH_VERSION
from observability import langfuse_tracing


@pytest.fixture(autouse=True)
def _disabled_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """キー未設定（＝送出無効）を既定にする。テストから Langfuse へ送らせない。"""
    monkeypatch.setattr(langfuse_tracing, "_client", None)


def test_build_graph_config_carries_thread_id_and_trace_attributes() -> None:
    session_id = uuid.uuid4()
    config = langfuse_tracing.build_graph_config(session_id=session_id, user_id="user-001", session_type="learning")

    assert config["configurable"]["thread_id"] == str(session_id)
    assert config["run_name"] == "learning-graph"
    assert config["metadata"]["langfuse_session_id"] == str(session_id)
    assert config["metadata"]["langfuse_user_id"] == "user-001"
    assert config["metadata"]["langfuse_tags"] == ["learning"]
    assert config["metadata"]["graph_version"] == GRAPH_VERSION


def test_build_graph_config_carries_no_callbacks_itself() -> None:
    """callbacks は trace のルート span が生きている間だけ付く（traced_graph_run 側の責務）。"""
    config = langfuse_tracing.build_graph_config(session_id=uuid.uuid4(), user_id="user-001", session_type="review")

    assert "callbacks" not in config


async def test_traced_graph_run_does_not_mutate_the_session_config() -> None:
    config = langfuse_tracing.build_graph_config(session_id=uuid.uuid4(), user_id="user-001", session_type="learning")

    async with langfuse_tracing.traced_graph_run(config, name="respond-to-user", input="こんにちは") as run:
        run.set_output("応答")
        run_config = run.config

    assert run_config is not config
    assert run_config["configurable"] == config["configurable"]
    assert "callbacks" not in config


async def test_traced_graph_run_adds_no_callbacks_when_tracing_disabled() -> None:
    config = langfuse_tracing.build_graph_config(session_id=uuid.uuid4(), user_id="user-001", session_type="review")

    async with langfuse_tracing.traced_graph_run(config, name="update-review-note", input=None) as run:
        assert "callbacks" not in run.config


def test_init_tracing_is_noop_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_config, "LANGFUSE_PUBLIC_KEY", None)
    monkeypatch.setattr(app_config, "LANGFUSE_SECRET_KEY", None)

    langfuse_tracing.init_tracing()

    assert not langfuse_tracing.is_enabled()
