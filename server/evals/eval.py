import argparse
import asyncio
import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field

from evals.checks import check_fingerprint, run_check
from evals.golden_yaml import dump_copy_block
from graph.llm import llm, llm_judge
from graph.nodes.learning_dialogue import learning_dialogue
from graph.prompts.question import PROMPT_FINGERPRINT, PROMPT_VERSION
from graph.state import LearningState

logger = logging.getLogger(__name__)

_GOLDEN_DIR = Path(__file__).parent / "datasets" / "golden"
_JSONL_PATH = Path(__file__).parent / "datasets" / "generate_questions.jsonl"
_REPORTS_DIR = Path(__file__).parent / "reports"

_JUDGE_MAX_ATTEMPTS = 3
_EVAL_USER_ID = "eval-regression"
_NOT_APPLICABLE = "na"

JUDGE_PROMPT = """\
## 役割
あなたは、学習支援 AI の応答を評価する専門家です。

## 評価対象
学習者と AI の会話履歴、および直近の AI 応答が与えられます。
判定するのは「直近の AI 応答」だけです。

## 学習トピック
{topic}

## 会話履歴
{conversation}

## 直近の AI 応答（判定対象）
{observed_output}

## 判定基準
次の記述が、直近の AI 応答について成り立っているかを判定してください。

{criterion}

## 注意事項
- 記述が成り立つなら holds=true、成り立たないなら holds=false を返してください。
- 応答の良し悪しは判断しません。記述が事実として当てはまるかだけを見ます。
- reason を先に書き、その reason に基づいて holds を決めてください。
- reason は 1〜2 文で、応答のどの箇所を根拠にしたかを引用してください。
- reason と holds は必ず両方とも出力してください。
"""

JUDGE_RETRY_SUFFIX = """
## 前回の出力の不備
前回の応答は構造化出力として解釈できませんでした:

{error}

reason と holds の両方を必ず含めてください。holds は true か false のどちらかです。
reason だけを返してはいけません。
"""


class JudgeResult(BaseModel):
    reason: str = Field(..., description="判定の根拠。1〜2文で、応答のどの箇所を根拠にしたかを引用する")
    holds: bool = Field(..., description="判定基準の記述が、判定対象の応答について成り立っているか")


@dataclass(frozen=True)
class SourceTrace:
    trace_id: str
    turn: int
    meta: dict[str, Any]
    input: dict[str, Any]
    observed_output: str


@dataclass(frozen=True)
class Generation:
    output: str
    turn_analysis: dict[str, Any] | None
    covered_aspects: list[dict[str, Any]]
    turn_count: int


@dataclass(frozen=True)
class AssertionOutcome:
    assertion_id: str
    assertion_type: str
    polarity: str
    holds: bool | None
    verdict: str
    human_verdict: str
    detail: str

    @property
    def applicable(self) -> bool:
        return self.verdict != _NOT_APPLICABLE

    @property
    def agrees(self) -> bool:
        return self.applicable and bool(self.human_verdict) and self.verdict == self.human_verdict


@dataclass
class RunResult:
    run_index: int
    output: str
    outcomes: list[AssertionOutcome]
    generation: Generation | None = None

    @property
    def verdict(self) -> str:
        return aggregate_verdict(self.outcomes)


@dataclass
class InstanceResult:
    failure_mode: str
    source_trace_id: str
    human_pass: bool | None
    runs: list[RunResult] = field(default_factory=list)


# 新しめの Anthropic モデルは `temperature` を受け付けず 400 を返す
# （invalid_request_error: `temperature` is deprecated for this model）。
_TEMPERATURE_UNSUPPORTED: frozenset[str] = frozenset({"claude-opus-5", "claude-sonnet-5"})


def resolve_judge(model: str | None) -> BaseChatModel:
    """`--judge-model` が指定されていればその Anthropic モデルを、無ければ既定の judge を返す。"""
    if model is None:
        return llm_judge
    if model in _TEMPERATURE_UNSUPPORTED:
        return ChatAnthropic(model=model)
    return ChatAnthropic(model=model, temperature=0)


def judge_model_name(judge: BaseChatModel) -> str:
    name = getattr(judge, "model", None) or getattr(judge, "model_name", None)
    return str(name) if name else type(judge).__name__


def load_golden_records() -> Iterator[dict[str, Any]]:
    for path in sorted(_GOLDEN_DIR.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f)
        if record.get("status") == "active":
            yield record


def validate_check_fingerprints() -> dict[str, str]:
    in_use: dict[str, str] = {}
    stale: list[str] = []
    for record in load_golden_records():
        for assertion in record["assertions"]:
            if assertion["type"] != "deterministic":
                continue
            current = check_fingerprint(assertion["check"])
            in_use[assertion["check"]] = current
            if assertion.get("check_fingerprint") != current:
                stale.append(
                    f"  {record['failure_mode']}/{assertion['id']}: check={assertion['check']} "
                    f"recorded={assertion.get('check_fingerprint')!r} current={current!r}"
                )
    if stale:
        raise ValueError(
            "deterministic check の実装が golden 記録時から変わっている。criterion を読み直し、"
            "必要なら human_verdicts を付け直してから check_fingerprint を更新すること:\n" + "\n".join(stale)
        )
    return in_use


def load_source_records() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with _JSONL_PATH.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                record: dict[str, Any] = json.loads(line)
                records[record["id"]] = record
    return records


def get_source_trace(trace_id: str, sources: dict[str, dict[str, Any]]) -> SourceTrace:
    try:
        record = sources[trace_id]
    except KeyError as exc:
        raise ValueError(f"unknown source_trace_id: {trace_id} not in {_JSONL_PATH}") from exc
    return SourceTrace(
        trace_id=trace_id,
        turn=record["turn"],
        meta=record["meta"],
        input=record["input"],
        observed_output=record["output"],
    )


def to_state(trace: SourceTrace) -> LearningState:
    graph_state = trace.input["graph_state"]
    messages: list[BaseMessage] = [
        AIMessage(content=m["content"]) if m["role"] == "assistant" else HumanMessage(content=m["content"])
        for m in trace.input["conversation_history"]
    ]
    state: LearningState = {
        "user_id": _EVAL_USER_ID,
        "dialogue_session_id": uuid4(),
        "note_id": uuid4(),
        "messages": messages,
        "topic": graph_state["topic"],
        "turn_count": trace.turn,
        "should_generate_note": False,
        "session_type": "learning",
    }
    if graph_state.get("learning_goal"):
        state["learning_goal"] = graph_state["learning_goal"]
    if graph_state.get("focus_aspects"):
        state["focus_aspects"] = graph_state["focus_aspects"]
    if graph_state.get("covered_aspects"):
        state["covered_aspects"] = graph_state["covered_aspects"]
    return state


def message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            parts.append(str(block.get("text", "")))
    return "".join(parts)


async def generate_output(trace: SourceTrace) -> Generation:
    """本番の対話ノードをそのまま呼んで応答を作り直す（regression モード）。

    事前分析を含めて実行するため、プロンプト改訂の効果と分析の揺れが両方入る。
    保存済み `turn_analysis` を注入する分離実行は、jsonl 側にその値が無いため今は行えない。
    """
    result = await learning_dialogue(to_state(trace))
    return Generation(
        output=message_text(result["messages"][0]),
        turn_analysis=result.get("turn_analysis"),
        covered_aspects=list(result.get("covered_aspects") or []),
        turn_count=result["turn_count"],
    )


def to_verdict(polarity: str, holds: bool) -> str:
    if polarity == "must":
        return "pass" if holds else "fail"
    if polarity == "must_not":
        return "fail" if holds else "pass"
    raise ValueError(f"unknown polarity: {polarity!r} (expected 'must' or 'must_not')")


def aggregate_verdict(outcomes: list[AssertionOutcome]) -> str:
    """must が満たされ must_not が現れていなければ pass。適用外（na）は中立。"""
    scored = [o for o in outcomes if o.applicable]
    return "pass" if all(o.verdict == "pass" for o in scored) else "fail"


def format_conversation(conversation_history: list[dict[str, str]]) -> str:
    return "\n".join(f"{turn['role']}: {turn['content']}" for turn in conversation_history)


async def judge_by_llm(
    assertion: dict[str, Any], trace: SourceTrace, output: str, judge: BaseChatModel
) -> JudgeResult:
    """1 criterion を二値で判定する。

    judge は必須フィールド `holds` を落とした tool_call を返すことがある。temperature 0 では
    同じプロンプトを投げ直しても同じ欠落が再現するため、リトライでは欠けたフィールドを
    名指しした追記を足して入力を変える。
    """
    prompt = JUDGE_PROMPT.format(
        topic=trace.input["graph_state"]["topic"],
        conversation=format_conversation(trace.input["conversation_history"]),
        observed_output=output,
        criterion=assertion["criterion"].strip(),
    )
    runnable = judge.with_structured_output(JudgeResult, include_raw=True)

    last_error: str = "unknown"
    for attempt in range(1, _JUDGE_MAX_ATTEMPTS + 1):
        content = prompt if attempt == 1 else f"{prompt}\n{JUDGE_RETRY_SUFFIX.format(error=last_error)}"
        try:
            result = await runnable.ainvoke([HumanMessage(content=content)])
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("judge attempt %d/%d raised for %s", attempt, _JUDGE_MAX_ATTEMPTS, assertion["id"])
            continue
        parsed = result["parsed"] if isinstance(result, dict) else result
        if isinstance(parsed, JudgeResult):
            return parsed
        last_error = str(result["parsing_error"]) if isinstance(result, dict) else "judge returned no JudgeResult"
        logger.warning("judge attempt %d/%d unparsable for %s", attempt, _JUDGE_MAX_ATTEMPTS, assertion["id"])

    raise RuntimeError(
        f"judge failed for assertion {assertion['id']} after {_JUDGE_MAX_ATTEMPTS} attempts: {last_error}"
    )


async def evaluate_assertion(
    assertion: dict[str, Any],
    trace: SourceTrace,
    output: str,
    human_verdicts: dict[str, str],
    judge: BaseChatModel,
    *,
    compare_to_human: bool,
) -> AssertionOutcome:
    declared = human_verdicts[assertion["id"]]
    human_verdict = declared if compare_to_human else ""

    # applies_when は input の性質なので、再生成した出力でも instance の na 宣言をそのまま使う。
    if declared == _NOT_APPLICABLE:
        return AssertionOutcome(
            assertion_id=assertion["id"],
            assertion_type=assertion["type"],
            polarity=assertion["polarity"],
            holds=None,
            verdict=_NOT_APPLICABLE,
            human_verdict=human_verdict,
            detail=f"applies_when: {assertion.get('applies_when', '').strip()}",
        )

    if assertion["type"] == "judge":
        judged = await judge_by_llm(assertion, trace, output, judge)
        holds, detail = judged.holds, judged.reason
    elif assertion["type"] == "deterministic":
        outcome = run_check(assertion["check"], output)
        holds, detail = outcome.holds, outcome.detail
    else:
        raise ValueError(f"unknown assertion type: {assertion['type']!r} (expected 'judge' or 'deterministic')")

    return AssertionOutcome(
        assertion_id=assertion["id"],
        assertion_type=assertion["type"],
        polarity=assertion["polarity"],
        holds=holds,
        verdict=to_verdict(assertion["polarity"], holds),
        human_verdict=human_verdict,
        detail=detail,
    )


async def evaluate_output(
    record: dict[str, Any],
    instance: dict[str, Any],
    trace: SourceTrace,
    output: str,
    judge: BaseChatModel,
    *,
    compare_to_human: bool,
) -> list[AssertionOutcome]:
    return list(
        await asyncio.gather(
            *(
                evaluate_assertion(
                    assertion,
                    trace,
                    output,
                    instance["human_verdicts"],
                    judge,
                    compare_to_human=compare_to_human,
                )
                for assertion in record["assertions"]
            )
        )
    )


async def evaluate_instance(
    record: dict[str, Any],
    instance: dict[str, Any],
    trace: SourceTrace,
    judge: BaseChatModel,
    *,
    mode: str,
    runs: int,
) -> InstanceResult:
    result = InstanceResult(
        failure_mode=record["failure_mode"],
        source_trace_id=instance["source_trace_id"],
        human_pass=instance.get("pass"),
    )
    compare_to_human = mode == "scoring"
    for run_index in range(1, (runs if mode == "regression" else 1) + 1):
        generation = await generate_output(trace) if mode == "regression" else None
        output = generation.output if generation else trace.observed_output
        outcomes = await evaluate_output(record, instance, trace, output, judge, compare_to_human=compare_to_human)
        result.runs.append(RunResult(run_index=run_index, output=output, outcomes=outcomes, generation=generation))
    return result


def print_instance(result: InstanceResult) -> None:
    print("=" * 100)
    print(f"failure_mode={result.failure_mode}  source_trace_id={result.source_trace_id}")
    print("-" * 100)
    for run in result.runs:
        if len(result.runs) > 1:
            analysis = run.generation.turn_analysis if run.generation else None
            print(f"[run {run.run_index}] verdict={run.verdict}  turn_analysis={analysis}")
            print(f"          {run.output[:120]}...")
        for outcome in run.outcomes:
            if not outcome.applicable:
                mark = "-- "
            elif not outcome.human_verdict:
                mark = "   "
            else:
                mark = "OK " if outcome.agrees else "NG "
            human = f" human={outcome.human_verdict}" if outcome.human_verdict else ""
            print(
                f"{mark}{outcome.assertion_id}  {outcome.assertion_type:<13} {outcome.polarity:<8} "
                f"holds={str(outcome.holds):<5} judged={outcome.verdict:<4}{human}"
            )
            print(f"      {outcome.detail}")
        print()


def assertion_pass_rates(results: list[InstanceResult]) -> list[dict[str, Any]]:
    rates: list[dict[str, Any]] = []
    for result in results:
        by_assertion: dict[str, list[str]] = {}
        for run in result.runs:
            for outcome in run.outcomes:
                by_assertion.setdefault(outcome.assertion_id, []).append(outcome.verdict)
        for assertion_id, verdicts in by_assertion.items():
            scored = [v for v in verdicts if v != _NOT_APPLICABLE]
            rates.append(
                {
                    "failure_mode": result.failure_mode,
                    "source_trace_id": result.source_trace_id,
                    "assertion_id": assertion_id,
                    "runs": len(verdicts),
                    "not_applicable": len(verdicts) - len(scored),
                    "passed": sum(1 for v in scored if v == "pass"),
                    "pass_rate": (sum(1 for v in scored if v == "pass") / len(scored)) if scored else None,
                }
            )
    return rates


def failure_mode_pass_rates(results: list[InstanceResult]) -> list[dict[str, Any]]:
    by_mode: dict[str, list[str]] = {}
    for result in results:
        for run in result.runs:
            by_mode.setdefault(result.failure_mode, []).append(run.verdict)
    return [
        {
            "failure_mode": mode,
            "runs": len(verdicts),
            "passed": sum(1 for v in verdicts if v == "pass"),
            "pass_rate": sum(1 for v in verdicts if v == "pass") / len(verdicts),
        }
        for mode, verdicts in sorted(by_mode.items())
    ]


def assertion_agreement(results: list[InstanceResult]) -> dict[str, Any]:
    outcomes = [o for r in results for run in r.runs for o in run.outcomes]
    scored = [o for o in outcomes if o.applicable and o.human_verdict]
    tp = sum(1 for o in scored if o.human_verdict == "fail" and o.verdict == "fail")
    fn = sum(1 for o in scored if o.human_verdict == "fail" and o.verdict == "pass")
    fp = sum(1 for o in scored if o.human_verdict == "pass" and o.verdict == "fail")
    tn = sum(1 for o in scored if o.human_verdict == "pass" and o.verdict == "pass")
    total = len(scored)
    return {
        "granularity": "assertion",
        "total": total,
        "agreed": tp + tn,
        "agreement_rate": (tp + tn) / total if total else None,
        "not_applicable": sum(1 for o in outcomes if not o.applicable),
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "tpr": tp / (tp + fn) if tp + fn else None,
        "tnr": tn / (tn + fp) if tn + fp else None,
        "mismatches": [
            {
                "failure_mode": r.failure_mode,
                "source_trace_id": r.source_trace_id,
                "assertion_id": o.assertion_id,
                "judged": o.verdict,
                "human": o.human_verdict,
                "detail": o.detail,
            }
            for r in results
            for run in r.runs
            for o in run.outcomes
            if o.applicable and o.human_verdict and not o.agrees
        ],
    }


def record_agreement(results: list[InstanceResult]) -> dict[str, Any]:
    """instance 全体の pass/fail を人間ラベル（instance["pass"]）と突き合わせる。"""
    pairs = [
        (run.verdict, "pass" if r.human_pass else "fail")
        for r in results
        if r.human_pass is not None
        for run in r.runs
    ]
    agreed = sum(1 for judged, human in pairs if judged == human)
    return {
        "granularity": "record",
        "total": len(pairs),
        "agreed": agreed,
        "agreement_rate": agreed / len(pairs) if pairs else None,
        "mismatches": [
            {
                "failure_mode": r.failure_mode,
                "source_trace_id": r.source_trace_id,
                "judged": run.verdict,
                "human": "pass" if r.human_pass else "fail",
            }
            for r in results
            if r.human_pass is not None
            for run in r.runs
            if run.verdict != ("pass" if r.human_pass else "fail")
        ],
    }


def assertion_agreement_rates(results: list[InstanceResult]) -> list[dict[str, Any]]:
    """assertion ごとに instance を跨いで judge–人間一致を集計する。

    pass 率は負例と正例で目標値が逆になり、コーパスの構成を知らないと読めない。
    scoring で見るべきは「judge がラベルと合っているか」なので、目標が常に 100% の指標にする。
    """
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for result in results:
        for run in result.runs:
            for outcome in run.outcomes:
                if not outcome.applicable or not outcome.human_verdict:
                    continue
                key = (result.failure_mode, outcome.assertion_id)
                row = rows.setdefault(
                    key,
                    {"failure_mode": key[0], "assertion_id": key[1], "total": 0, "agreed": 0, "mismatches": []},
                )
                row["total"] += 1
                if outcome.agrees:
                    row["agreed"] += 1
                else:
                    row["mismatches"].append(
                        {
                            "source_trace_id": result.source_trace_id,
                            "judged": outcome.verdict,
                            "human": outcome.human_verdict,
                        }
                    )
    return [rows[key] for key in sorted(rows)]


def _instance_kind(human_pass: bool | None) -> str:
    if human_pass is None:
        return "未ラベル"
    return "正例" if human_pass else "負例"


def print_scoring_summary(report: dict[str, Any]) -> None:
    print("レコード別判定（judge の集約 vs 人間ラベル）")
    for record in report["records"]:
        human = "-" if record["human_pass"] is None else ("pass" if record["human_pass"] else "fail")
        for run in record["runs"]:
            mark = "OK" if human != "-" and run["verdict"] == human else "NG"
            print(
                f"  {record['source_trace_id']:<45} {_instance_kind(record['human_pass']):<6} "
                f"judged={run['verdict']:<5} human={human:<5} {mark}"
            )
    record_agreement_result = report["agreement"]["record"]
    rate = record_agreement_result["agreement_rate"]
    suffix = f" ({rate:.0%})" if rate is not None else ""
    print(f"{' ' * 66}一致 {record_agreement_result['agreed']}/{record_agreement_result['total']}{suffix}")

    print("\nassertion 別 一致")
    for row in report["agreement"]["by_assertion"]:
        print(f"  {row['failure_mode']:<38} {row['assertion_id']:<4} {row['agreed']}/{row['total']}")
        for mismatch in row["mismatches"]:
            print(f"      NG {mismatch['source_trace_id']}  judged={mismatch['judged']} human={mismatch['human']}")

    agreement = report["agreement"]["assertion"]
    matrix = agreement["confusion_matrix"]
    rate = agreement["agreement_rate"]
    suffix = f" ({rate:.0%})" if rate is not None else ""
    print(f"\njudge–人間一致（assertion 単位）: {agreement['agreed']}/{agreement['total']}{suffix}")
    counts = f"TP={matrix['tp']} TN={matrix['tn']} FP={matrix['fp']} FN={matrix['fn']}"
    print(f"  {counts}   （陽性 = 人間ラベル fail）")
    print(f"  TPR={agreement['tpr']:.0%}" if agreement["tpr"] is not None else "  TPR=n/a")
    print(f"  TNR={agreement['tnr']:.0%}" if agreement["tnr"] is not None else "  TNR=n/a")
    print(f"  適用外（applies_when を満たさず採点対象外）: {agreement['not_applicable']} 件")


def print_regression_summary(report: dict[str, Any]) -> None:
    print(f"失敗モード別 pass 率（{report['meta']['runs']} 回生成）")
    for row in report["aggregate"]["failure_mode_pass_rates"]:
        print(f"  {row['failure_mode']:<38} {row['passed']}/{row['runs']} ({row['pass_rate']:.0%})")

    print("\nassertion 別 pass 率")
    for row in report["aggregate"]["assertion_pass_rates"]:
        rate = f"{row['pass_rate']:.0%}" if row["pass_rate"] is not None else "n/a"
        na = f"  na={row['not_applicable']}" if row["not_applicable"] else ""
        print(
            f"  {row['source_trace_id']:<45} {row['assertion_id']:<4} "
            f"{row['passed']}/{row['runs'] - row['not_applicable']} ({rate}){na}"
        )
    print("\n人間ラベルが無いため judge–人間一致は算出しない（scoring モードで校正する）。")


def print_summary(report: dict[str, Any]) -> None:
    print("=" * 100)
    if report["meta"]["mode"] == "scoring":
        print_scoring_summary(report)
    else:
        print_regression_summary(report)

    if report["errors"]:
        print("\nエラー")
        for err in report["errors"]:
            print(f"  {err}")


def build_report(
    results: list[InstanceResult],
    errors: list[str],
    *,
    mode: str,
    runs: int,
    fingerprints: dict[str, str],
    judge: BaseChatModel,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "meta": {
            "mode": mode,
            "runs": runs if mode == "regression" else 1,
            "generated_at": datetime.now(UTC).isoformat(),
            "model": llm.model_name,
            "temperature": llm.temperature,
            "prompt_version": PROMPT_VERSION,
            "prompt_fingerprint": PROMPT_FINGERPRINT,
            "judge_model": judge_model_name(judge),
            "check_fingerprints": fingerprints,
        },
        "records": [
            {
                "failure_mode": r.failure_mode,
                "source_trace_id": r.source_trace_id,
                "human_pass": r.human_pass,
                "runs": [
                    {
                        "run_index": run.run_index,
                        "verdict": run.verdict,
                        "output": run.output,
                        "turn_analysis": run.generation.turn_analysis if run.generation else None,
                        "assertions": [
                            {
                                "assertion_id": o.assertion_id,
                                "type": o.assertion_type,
                                "polarity": o.polarity,
                                "holds": o.holds,
                                "judged": o.verdict,
                                "human": o.human_verdict or None,
                                "detail": o.detail,
                            }
                            for o in run.outcomes
                        ],
                    }
                    for run in r.runs
                ],
            }
            for r in results
        ],
        "aggregate": {
            "assertion_pass_rates": assertion_pass_rates(results),
            "failure_mode_pass_rates": failure_mode_pass_rates(results),
        },
        "errors": errors,
    }
    if mode == "scoring":
        report["agreement"] = {
            "assertion": assertion_agreement(results),
            "record": record_agreement(results),
            "by_assertion": assertion_agreement_rates(results),
        }
    return report


def next_rerun_id(source_trace_id: str, existing: set[str]) -> str:
    """`{元 id}-rerun{連番}` の空き番号を返す。採取セッションを重ねても既存 id を踏まない。"""
    index = 1
    while f"{source_trace_id}-rerun{index:02d}" in existing:
        index += 1
    return f"{source_trace_id}-rerun{index:02d}"


def emit_jsonl(path: Path, results: list[InstanceResult], sources: dict[str, dict[str, Any]]) -> list[str]:
    """regression の生成を正本 jsonl へ追記する。input は元 instance のものを引き継ぐ。

    既存行は書き換えず追記だけする（近傍事例の採取が主目的で、annotate は人間が後から行う）。
    """
    existing = set(sources)
    written: list[str] = []
    with path.open("a", encoding="utf-8") as f:
        for result in results:
            base = sources[result.source_trace_id]
            for run in result.runs:
                if run.generation is None:
                    continue
                trace_id = next_rerun_id(result.source_trace_id, existing)
                graph_state = dict(base["input"]["graph_state"])
                graph_state["covered_aspects"] = run.generation.covered_aspects
                graph_state["turn_count"] = run.generation.turn_count
                graph_state["turn_analysis"] = run.generation.turn_analysis
                record = {
                    "id": trace_id,
                    "schema_version": base["schema_version"],
                    "source": "synthetic",
                    "session": base["session"],
                    "dialogue_session_id": None,
                    "turn": base["turn"],
                    "captured_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "meta": {
                        "model": llm.model_name,
                        "prompt_version": PROMPT_VERSION,
                        "prompt_fingerprint": PROMPT_FINGERPRINT,
                        "params": {"temperature": llm.temperature},
                    },
                    "input": {
                        "conversation_history": base["input"]["conversation_history"],
                        "graph_state": graph_state,
                    },
                    "output": run.generation.output,
                    "pass": None,
                    "first_failure": None,
                    "note": f"regression 再実行（{result.source_trace_id} の入力を再利用）。未 annotate",
                    "annotated_at": None,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                existing.add(trace_id)
                written.append(trace_id)
    return written


async def run(mode: str, runs: int, judge: BaseChatModel) -> tuple[list[InstanceResult], list[str], dict[str, str]]:
    fingerprints = validate_check_fingerprints()
    sources = load_source_records()

    results: list[InstanceResult] = []
    errors: list[str] = []
    for record in load_golden_records():
        # 正例と負例は同じターンの別応答なので input が一致する。regression は input から作り直すため、
        # instance ごとに回すと同じ入力を二重に生成して pass 率が重複計上される。
        seen_inputs: set[str] = set()
        for instance in record["instances"]:
            label = f"{record['failure_mode']}/{instance['source_trace_id']}"
            try:
                trace = get_source_trace(instance["source_trace_id"], sources)
            except Exception as exc:
                logger.exception("instance failed: %s", label)
                errors.append(f"{label}: {type(exc).__name__}: {exc}")
                continue

            if mode == "regression":
                fingerprint = json.dumps(trace.input, ensure_ascii=False, sort_keys=True)
                if fingerprint in seen_inputs:
                    print(f"skip {label}: 同一 input の instance を再生成済み")
                    continue
                seen_inputs.add(fingerprint)

            try:
                result = await evaluate_instance(record, instance, trace, judge, mode=mode, runs=runs)
            except Exception as exc:
                logger.exception("instance failed: %s", label)
                errors.append(f"{label}: {type(exc).__name__}: {exc}")
                continue
            print_instance(result)
            results.append(result)
    return results, errors, fingerprints


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="evals.eval", description="golden レコードに対する eval ランナー")
    parser.add_argument("--mode", choices=("scoring", "regression"), default="scoring")
    parser.add_argument("--runs", type=int, default=3, help="regression の1インスタンスあたり生成回数")
    parser.add_argument("--out", type=Path, default=None, help="レポートの出力先（既定は evals/reports/）")
    parser.add_argument("--emit-jsonl", type=Path, default=None, help="regression の生成を正本 jsonl へ追記する")
    parser.add_argument("--emit-instance", default=None, help="trace id を指定して golden 用の写しを出力する")
    parser.add_argument(
        "--judge-model",
        default=None,
        help="judge に使う Anthropic モデル（既定は graph.llm の llm_judge）。criterion の曖昧さは"
        "モデル間の判定の割れとして現れるため、複数モデルで確認する",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    if args.emit_instance:
        print(dump_copy_block(load_source_records()[args.emit_instance]), end="")
        return

    judge = resolve_judge(args.judge_model)
    print(f"mode={args.mode} model={llm.model_name} temperature={llm.temperature}")
    print(f"judge={judge_model_name(judge)} prompt_version={PROMPT_VERSION} prompt_fingerprint={PROMPT_FINGERPRINT}\n")

    results, errors, fingerprints = await run(args.mode, args.runs, judge)
    report = build_report(results, errors, mode=args.mode, runs=args.runs, fingerprints=fingerprints, judge=judge)
    print_summary(report)

    out = args.out or _REPORTS_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{args.mode}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nreport: {out}")

    if args.emit_jsonl:
        written = emit_jsonl(args.emit_jsonl, results, load_source_records())
        print(f"emitted {len(written)} record(s) to {args.emit_jsonl}")


if __name__ == "__main__":
    asyncio.run(main())
