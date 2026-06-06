from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _stub_trace_persistence() -> Generator[None]:
    """ユニットテストではトレース永続化を一律で無効化する。

    measured_ainvoke / measured_node の `_save_trace_safely` は実 DB プール
    （`core.database.get_pool` のプロセスグローバルなキャッシュ）に接続する。ユニットテストでこれを
    呼ぶと、テストごとに異なるイベントループ上で接続がリークし、プールサイズを超えた時点で
    `acquire()` が無限ブロックしてスイートがハングする（テストの実行順・件数に依存して顕在化する）。
    そのため実 DB に触れさせないようスタブ化する。トレース挙動自体を検証するテストは各自で
    再パッチして上書きするため、本フィクスチャと衝突しない。
    """
    with (
        patch("observability.llm._save_trace_safely", new=AsyncMock()),
        patch("observability.tracing._save_trace_safely", new=AsyncMock()),
    ):
        yield
