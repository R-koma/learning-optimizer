"""Eval runner for phase-2 measurement harness.

Usage:
    uv run python -m evals.runner --task note_generation --smoke
    uv run python -m evals.runner --task note_generation --trials 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import statistics
import subprocess
import sys
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from evals.graders import (
    dialogue_ended_correctly,
    feedback_is_actionable,
    note_has_sections,
    note_quality_judge,
    response_label_match,
)
from evals.graders.base import GraderResult
from graph.llm import llm as default_llm
from graph.llm import llm_structured as default_llm_structured
from graph.model import FeedbackOutput, NoteContent
from graph.prompts import (
    ANALYZE_RESPONSE_PROMPT,
    GENERATE_FEEDBACK_PROMPT,
    GENERATE_NOTE_PROMPT,
    GENERATE_QUESTION_PROMPT,
    REVIEW_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

DATASETS_DIR = Path(__file__).parent / "datasets"
REPORTS_DIR = Path(__file__).parent / "reports"
SMOKE_MAX_CASES = 5

TaskName = Literal[
    "note_generation",
    "feedback_generation",
    "question_generation",
    "response_analysis",
]
TASK_NAMES: tuple[TaskName, ...] = (
    "note_generation",
    "feedback_generation",
    "question_generation",
    "response_analysis",
)


@dataclass
class CaseResult:
    case_id: str
    trial: int
    grader_results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@dataclass
class EvalReport:
    task: str
    run_at: str
    git_sha: str
    n_cases: int
    n_trials: int
    smoke: bool
    judge_enabled: bool
    case_results: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, float] = field(default_factory=dict)


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _load_dataset(task: TaskName, *, smoke: bool = False) -> list[dict[str, Any]]:
    path = DATASETS_DIR / f"{task}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"dataset not found: {path}")
    cases: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    if smoke:
        cases = cases[:SMOKE_MAX_CASES]
    return cases


def _build_conversation_text(conversation: Iterable[dict[str, str]]) -> str:
    lines: list[str] = []
    for msg in conversation:
        role = "ユーザー" if msg["role"] == "user" else "アシスタント"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


async def _invoke_note_generation(case: dict[str, Any], llm_structured: ChatOpenAI) -> NoteContent:
    conversation_text = _build_conversation_text(case["conversation"])
    structured = llm_structured.with_structured_output(NoteContent)
    result = await structured.ainvoke(
        [
            SystemMessage(content=GENERATE_NOTE_PROMPT),
            {"role": "user", "content": conversation_text},
        ]
    )
    if not isinstance(result, NoteContent):
        raise TypeError(f"expected NoteContent, got {type(result).__name__}")
    return result


async def _invoke_feedback_generation(case: dict[str, Any], llm_structured: ChatOpenAI) -> FeedbackOutput:
    conversation_history = _build_conversation_text(case["conversation"])
    analyze_prompt = ANALYZE_RESPONSE_PROMPT.format(topic=case["topic"], conversation_history=conversation_history)
    analysis_response = await llm_structured.ainvoke([SystemMessage(content=analyze_prompt)])
    analysis_text = (
        analysis_response.content if isinstance(analysis_response.content, str) else str(analysis_response.content)
    )

    feedback_prompt = GENERATE_FEEDBACK_PROMPT.format(topic=case["topic"], analysis=analysis_text)
    note_payload = f"トピック: {case['topic']}\n\n{case['note_content']}"
    structured = llm_structured.with_structured_output(FeedbackOutput)
    result = await structured.ainvoke(
        [
            SystemMessage(content=feedback_prompt),
            {"role": "user", "content": note_payload},
        ]
    )
    if not isinstance(result, FeedbackOutput):
        raise TypeError(f"expected FeedbackOutput, got {type(result).__name__}")
    return result


async def _invoke_question_generation(case: dict[str, Any], llm: ChatOpenAI) -> str:
    recent_messages = f"ユーザー: {case['user_message']}"
    prompt = GENERATE_QUESTION_PROMPT.format(topic=case["topic"], recent_messages=recent_messages)
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    return response.content if isinstance(response.content, str) else str(response.content)


async def _invoke_response_analysis(case: dict[str, Any], llm: ChatOpenAI) -> str:
    review_prompt = REVIEW_SYSTEM_PROMPT.format(
        topic=case["topic"],
        content=case.get("note_content", ""),
        summary=case.get("note_summary", ""),
    )
    history_text = _build_conversation_text(case["conversation"])
    user_text = f"以下は復習対話の履歴です。\n\n{history_text}\n\n最後のユーザー発言: {case['user_message']}"
    response = await llm.ainvoke(
        [
            SystemMessage(content=review_prompt),
            {"role": "user", "content": user_text},
        ]
    )
    return response.content if isinstance(response.content, str) else str(response.content)


async def _grade_note_generation_case(
    case: dict[str, Any],
    *,
    llm_structured: ChatOpenAI,
    judge_llm: ChatOpenAI | None,
) -> list[GraderResult]:
    note = await _invoke_note_generation(case, llm_structured)
    results = [note_has_sections.grade(note.content)]
    if judge_llm is not None:
        conversation_text = _build_conversation_text(case["conversation"])
        results.append(
            await note_quality_judge.grade(
                note_content=note.content,
                conversation_text=conversation_text,
                judge_llm=judge_llm,
            )
        )
    return results


async def _grade_feedback_generation_case(case: dict[str, Any], *, llm_structured: ChatOpenAI) -> list[GraderResult]:
    feedback = await _invoke_feedback_generation(case, llm_structured)
    return [feedback_is_actionable.grade(feedback)]


async def _grade_question_generation_case(case: dict[str, Any], *, llm: ChatOpenAI) -> list[GraderResult]:
    response = await _invoke_question_generation(case, llm)
    is_nonempty = bool(response.strip())
    has_question_mark = "？" in response or "?" in response
    passed = is_nonempty and has_question_mark
    return [
        GraderResult(
            grader_name="question_generation_smoke",
            score=1.0 if passed else 0.0,
            passed=passed,
            reason="response is non-empty and contains a question mark"
            if passed
            else "response is empty or missing question mark",
            metadata={"is_nonempty": is_nonempty, "has_question_mark": has_question_mark},
        )
    ]


async def _grade_response_analysis_case(case: dict[str, Any], *, llm: ChatOpenAI) -> list[GraderResult]:
    response = await _invoke_response_analysis(case, llm)
    expected = case["expected_label"]
    return [
        dialogue_ended_correctly.grade(response_content=response, expected_label=expected),
        response_label_match.grade(response_content=response, expected_label=expected),
    ]


async def _run_case(
    task: TaskName,
    case: dict[str, Any],
    *,
    llm: ChatOpenAI,
    llm_structured: ChatOpenAI,
    judge_llm: ChatOpenAI | None,
) -> list[GraderResult]:
    if task == "note_generation":
        return await _grade_note_generation_case(case, llm_structured=llm_structured, judge_llm=judge_llm)
    if task == "feedback_generation":
        return await _grade_feedback_generation_case(case, llm_structured=llm_structured)
    if task == "question_generation":
        return await _grade_question_generation_case(case, llm=llm)
    if task == "response_analysis":
        return await _grade_response_analysis_case(case, llm=llm)
    raise ValueError(f"unknown task: {task}")


def _summarize(case_results: list[CaseResult]) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for cr in case_results:
        for gr in cr.grader_results:
            grouped[gr["grader_name"]].append(float(gr["score"]))
    return {name: statistics.mean(scores) for name, scores in grouped.items() if scores}


def _save_report(report: EvalReport) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = REPORTS_DIR / f"{report.task}_{report.git_sha}_{timestamp}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(asdict(report), f, ensure_ascii=False, indent=2)
    return path


async def run_eval(
    task: TaskName,
    *,
    n_trials: int = 1,
    smoke: bool = False,
    save_report: bool = True,
    judge_enabled: bool = False,
    llm: ChatOpenAI | None = None,
    llm_structured: ChatOpenAI | None = None,
    judge_llm: ChatOpenAI | None = None,
) -> EvalReport:
    cases = _load_dataset(task, smoke=smoke)
    effective_llm = llm or default_llm
    effective_structured = llm_structured or default_llm_structured
    effective_judge: ChatOpenAI | None = None
    if judge_enabled and task == "note_generation":
        effective_judge = judge_llm or ChatOpenAI(model="gpt-4o", temperature=0)  # type: ignore[call-arg]

    case_results: list[CaseResult] = []
    for case in cases:
        for trial in range(n_trials):
            cr = CaseResult(case_id=case["id"], trial=trial)
            try:
                grader_results = await _run_case(
                    task,
                    case,
                    llm=effective_llm,
                    llm_structured=effective_structured,
                    judge_llm=effective_judge,
                )
                cr.grader_results = [asdict(gr) for gr in grader_results]
            except Exception as exc:
                logger.exception("eval case failed: case_id=%s trial=%d", case["id"], trial)
                cr.error = f"{type(exc).__name__}: {exc}"
            case_results.append(cr)

    report = EvalReport(
        task=task,
        run_at=datetime.now(UTC).isoformat(),
        git_sha=_git_sha(),
        n_cases=len(cases),
        n_trials=n_trials,
        smoke=smoke,
        judge_enabled=effective_judge is not None,
        case_results=[asdict(cr) for cr in case_results],
        summary=_summarize(case_results),
    )
    if save_report:
        path = _save_report(report)
        logger.info("eval report saved: %s", path)
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase-2 eval harness runner")
    parser.add_argument("--task", required=True, choices=TASK_NAMES)
    parser.add_argument("--smoke", action="store_true", help="run only first 5 cases")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--judge", action="store_true", help="enable LLM-as-judge (note_generation only)")
    parser.add_argument("--no-save", action="store_true", help="skip writing report JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = _parse_args(argv)
    report = asyncio.run(
        run_eval(
            cast(TaskName, args.task),
            n_trials=args.trials,
            smoke=args.smoke,
            judge_enabled=args.judge,
            save_report=not args.no_save,
        )
    )
    print(
        json.dumps(
            {"task": report.task, "summary": report.summary, "n_cases": report.n_cases},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
