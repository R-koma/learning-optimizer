"""regression / scoring の生成・採点を保存し、途中で切れた実行を再開できるようにする。

長時間実行が一瞬の接続断や課金上限で壊れると、生成し直し・判定し直しに時間と judge の
課金がかかる（`docs/note/2026-09-14-open-issues.md` B-9・C-2）。ここでは実行ごとに
1 つの保存先ディレクトリを持ち、run 単位で生成と採点を保存する。

保存済みの生成が拾えるかどうかは `manifest.json` の内容一致だけで判断する。生成本文の
ハッシュ一致は「その run の採点が今の生成と対応しているか」だけを保証し、golden の
criterion が変わっていないことまでは保証しない（criterion の変更は生成本文を変えない）。
そのため manifest には prompt / judge / check の fingerprint に加え、golden・rubric の
YAML 本文のハッシュも含め、いずれかが変わっていれば再開そのものを拒否する。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ManifestMismatch(RuntimeError):
    """再開先の実行条件が、保存済みの manifest と食い違う。"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_content_hash(*directories: Path) -> str:
    """golden・rubric の YAML 本文のハッシュ。criterion の書き換えを manifest 不一致として検知する。"""
    hasher = hashlib.sha256()
    for directory in directories:
        for path in sorted(directory.glob("*.yaml")):
            if path.name.startswith("_"):
                continue
            hasher.update(path.name.encode())
            hasher.update(path.read_bytes())
    return hasher.hexdigest()


class CheckpointStore:
    """1 回の実行に対応する保存先ディレクトリ。"""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.manifest_path = root / "manifest.json"

    def ensure_manifest(self, expected: dict[str, Any]) -> None:
        """初回は書き込むだけ。既存なら、今回の実行条件と食い違う項目がないか確認する。"""
        if not self.manifest_path.exists():
            write_json(self.manifest_path, expected)
            return
        recorded = read_json(self.manifest_path)
        mismatched = {key: (recorded.get(key), value) for key, value in expected.items() if recorded.get(key) != value}
        if mismatched:
            detail = "\n".join(f"  {key}: recorded={r!r} now={n!r}" for key, (r, n) in mismatched.items())
            raise ManifestMismatch(
                f"{self.root} の実行条件が保存済み manifest と食い違う。"
                f"別の --checkpoint-dir を使うか、条件を揃えること:\n{detail}"
            )

    def _stem(self, failure_mode: str, source_trace_id: str, run_index: int) -> str:
        safe = f"{failure_mode}__{source_trace_id}".replace("/", "_")
        return f"{safe}__run{run_index}"

    def generation_path(self, failure_mode: str, source_trace_id: str, run_index: int) -> Path:
        return self.root / "generations" / f"{self._stem(failure_mode, source_trace_id, run_index)}.json"

    def score_path(self, failure_mode: str, source_trace_id: str, run_index: int) -> Path:
        return self.root / "scores" / f"{self._stem(failure_mode, source_trace_id, run_index)}.json"

    def load_generation(self, failure_mode: str, source_trace_id: str, run_index: int) -> dict[str, Any] | None:
        path = self.generation_path(failure_mode, source_trace_id, run_index)
        return read_json(path) if path.exists() else None

    def save_generation(self, failure_mode: str, source_trace_id: str, run_index: int, data: dict[str, Any]) -> None:
        write_json(self.generation_path(failure_mode, source_trace_id, run_index), data)

    def load_score(self, failure_mode: str, source_trace_id: str, run_index: int) -> dict[str, Any] | None:
        path = self.score_path(failure_mode, source_trace_id, run_index)
        return read_json(path) if path.exists() else None

    def save_score(self, failure_mode: str, source_trace_id: str, run_index: int, data: dict[str, Any]) -> None:
        write_json(self.score_path(failure_mode, source_trace_id, run_index), data)
