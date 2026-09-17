"""annotate UI の HTTP 面（ローカル専用・認証なし）。

`create_app` をファクトリにしているのは、テストが tmp_path のデータセットへ TestClient を
張れるようにするため。
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from evals.taxonomy import FAILURE_MODES
from evals.tools.annotate.store import (
    DEFAULT_GOLDEN_DIR,
    DEFAULT_JSONL_PATH,
    Annotation,
    AnnotationError,
    assertions_by_failure_mode,
    deterministic_outcomes,
    golden_instances,
    load_records,
    save_annotation,
)

_INDEX = Path(__file__).parent / "static" / "index.html"


class AnnotationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    verdict: bool | None = Field(default=None, alias="pass")
    first_failure: str | None = None
    note: str = ""


def _summary(record: dict[str, Any], promoted_to: str | None) -> dict[str, Any]:
    return {
        "id": record["id"],
        "session": record["session"],
        "turn": record["turn"],
        "source": record["source"],
        "pass": record["pass"],
        "first_failure": record["first_failure"],
        "note": record["note"],
        "annotated_at": record["annotated_at"],
        "annotated": record["pass"] is not None,
        "promoted_to": promoted_to,
        "meta": record["meta"],
    }


def create_app(*, jsonl_path: Path = DEFAULT_JSONL_PATH, golden_dir: Path = DEFAULT_GOLDEN_DIR) -> FastAPI:
    app = FastAPI(title="eval annotate", docs_url=None, redoc_url=None)

    def _find(trace_id: str) -> dict[str, Any]:
        for record in load_records(jsonl_path):
            if record["id"] == trace_id:
                return record
        raise HTTPException(status_code=404, detail=f"unknown trace id: {trace_id}")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_INDEX)

    @app.get("/api/records")
    def list_records() -> dict[str, Any]:
        promoted = golden_instances(golden_dir)
        summaries = [
            _summary(record, promoted[record["id"]].failure_mode if record["id"] in promoted else None)
            for record in load_records(jsonl_path)
        ]
        return {"records": sorted(summaries, key=lambda s: bool(s["annotated"]))}

    @app.get("/api/records/{trace_id}")
    def get_record(trace_id: str) -> dict[str, Any]:
        record = _find(trace_id)
        promoted = golden_instances(golden_dir).get(trace_id)
        return {
            "record": _summary(record, promoted.failure_mode if promoted else None),
            "conversation_history": record["input"]["conversation_history"],
            "graph_state": record["input"]["graph_state"],
            "output": record["output"],
            "turn_decision": record.get("turn_decision"),
            "failure_modes": [{"key": key, "description": FAILURE_MODES[key]} for key in sorted(FAILURE_MODES)],
            "assertions": assertions_by_failure_mode(golden_dir),
            "deterministic_outcomes": [asdict(o) for o in deterministic_outcomes(record["output"], golden_dir)],
        }

    @app.put("/api/records/{trace_id}/annotation")
    def put_annotation(trace_id: str, payload: AnnotationPayload) -> dict[str, Any]:
        _find(trace_id)
        annotation = Annotation(
            verdict=payload.verdict, first_failure=payload.first_failure, note=payload.note.strip()
        )
        try:
            updated = save_annotation(jsonl_path, trace_id, annotation, golden_dir=golden_dir)
        except AnnotationError as exc:
            raise HTTPException(status_code=422, detail={"problems": exc.problems}) from exc
        promoted = golden_instances(golden_dir).get(trace_id)
        return {"record": _summary(updated, promoted.failure_mode if promoted else None)}

    return app
