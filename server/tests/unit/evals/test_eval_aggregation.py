"""eval.py の集計・一致率・入力変換の純関数。

judge 呼び出しと生成は API を叩くので対象外。ここで守るのは、この eval が出す数字そのもの
（混同行列・pass 率・レコード単位の集約）と、na を分母から外す扱い。
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from evals.eval import (
    AssertionOutcome,
    Generation,
    InstanceResult,
    RunResult,
    SourceTrace,
    aggregate_verdict,
    assertion_agreement,
    assertion_pass_rates,
    failure_mode_pass_rates,
    format_conversation,
    get_source_trace,
    load_source_records,
    message_text,
    next_rerun_id,
    record_agreement,
    to_state,
    to_verdict,
)


def outcome(
    assertion_id: str = "a1",
    *,
    polarity: str = "must",
    verdict: str = "pass",
    human: str = "",
    assertion_type: str = "judge",
) -> AssertionOutcome:
    return AssertionOutcome(
        assertion_id=assertion_id,
        assertion_type=assertion_type,
        polarity=polarity,
        holds=None,
        verdict=verdict,
        human_verdict=human,
        detail="",
    )


def instance(failure_mode: str, trace_id: str, human_pass: bool | None, runs: list[RunResult]) -> InstanceResult:
    return InstanceResult(failure_mode=failure_mode, source_trace_id=trace_id, human_pass=human_pass, runs=runs)


class TestToVerdict:
    def test_must_maps_holds_to_pass(self) -> None:
        assert to_verdict("must", True) == "pass"
        assert to_verdict("must", False) == "fail"

    def test_must_not_inverts(self) -> None:
        assert to_verdict("must_not", True) == "fail"
        assert to_verdict("must_not", False) == "pass"

    def test_unknown_polarity_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown polarity"):
            to_verdict("should", True)


class TestAggregateVerdict:
    def test_all_pass(self) -> None:
        assert aggregate_verdict([outcome("a1"), outcome("a2", polarity="must_not")]) == "pass"

    def test_single_fail_fails_the_record(self) -> None:
        assert aggregate_verdict([outcome("a1"), outcome("a2", verdict="fail")]) == "fail"

    def test_na_is_neutral(self) -> None:
        assert aggregate_verdict([outcome("a1"), outcome("a2", verdict="na")]) == "pass"

    def test_all_na_passes(self) -> None:
        assert aggregate_verdict([outcome("a1", verdict="na")]) == "pass"


class TestAssertionOutcomeFlags:
    def test_na_is_not_applicable_and_never_agrees(self) -> None:
        na = outcome(verdict="na", human="na")
        assert not na.applicable
        assert not na.agrees

    def test_missing_human_label_never_agrees(self) -> None:
        assert not outcome(verdict="pass", human="").agrees

    def test_matching_labels_agree(self) -> None:
        assert outcome(verdict="pass", human="pass").agrees


class TestAssertionAgreement:
    def test_confusion_matrix_treats_human_fail_as_positive(self) -> None:
        runs = [
            RunResult(
                run_index=1,
                output="",
                outcomes=[
                    outcome("a1", verdict="fail", human="fail"),  # TP
                    outcome("a2", verdict="pass", human="pass"),  # TN
                    outcome("a3", verdict="fail", human="pass"),  # FP
                    outcome("a4", verdict="pass", human="fail"),  # FN
                ],
            )
        ]
        result = assertion_agreement([instance("fm", "t1", False, runs)])

        assert result["confusion_matrix"] == {"tp": 1, "tn": 1, "fp": 1, "fn": 1}
        assert result["total"] == 4
        assert result["agreed"] == 2
        assert result["agreement_rate"] == 0.5
        assert result["tpr"] == 0.5
        assert result["tnr"] == 0.5

    def test_na_is_excluded_from_the_denominator_but_counted(self) -> None:
        runs = [
            RunResult(
                run_index=1,
                output="",
                outcomes=[outcome("a1", verdict="pass", human="pass"), outcome("a2", verdict="na", human="na")],
            )
        ]
        result = assertion_agreement([instance("fm", "t1", True, runs)])

        assert result["total"] == 1
        assert result["not_applicable"] == 1

    def test_mismatches_list_names_the_assertion(self) -> None:
        runs = [RunResult(run_index=1, output="", outcomes=[outcome("a2", verdict="fail", human="pass")])]
        result = assertion_agreement([instance("fm", "t1", True, runs)])

        assert [m["assertion_id"] for m in result["mismatches"]] == ["a2"]

    def test_empty_input_yields_no_rate(self) -> None:
        assert assertion_agreement([])["agreement_rate"] is None


class TestRecordAgreement:
    def test_compares_aggregated_verdict_with_instance_pass(self) -> None:
        passing = RunResult(run_index=1, output="", outcomes=[outcome("a1", verdict="pass")])
        failing = RunResult(run_index=1, output="", outcomes=[outcome("a1", verdict="fail")])
        results = [
            instance("fm", "positive", True, [passing]),
            instance("fm", "negative", False, [failing]),
            instance("fm", "mislabeled", True, [failing]),
        ]
        result = record_agreement(results)

        assert result["total"] == 3
        assert result["agreed"] == 2
        assert [m["source_trace_id"] for m in result["mismatches"]] == ["mislabeled"]

    def test_instances_without_human_label_are_skipped(self) -> None:
        runs = [RunResult(run_index=1, output="", outcomes=[outcome("a1")])]
        assert record_agreement([instance("fm", "t1", None, runs)])["total"] == 0


class TestPassRates:
    def test_assertion_pass_rate_counts_runs_and_excludes_na(self) -> None:
        results = [
            instance(
                "fm",
                "t1",
                False,
                [
                    RunResult(1, "", [outcome("a1", verdict="pass"), outcome("a2", verdict="na")]),
                    RunResult(2, "", [outcome("a1", verdict="fail"), outcome("a2", verdict="na")]),
                ],
            )
        ]
        rates = {row["assertion_id"]: row for row in assertion_pass_rates(results)}

        assert rates["a1"]["runs"] == 2
        assert rates["a1"]["passed"] == 1
        assert rates["a1"]["pass_rate"] == 0.5
        assert rates["a2"]["not_applicable"] == 2
        assert rates["a2"]["pass_rate"] is None

    def test_failure_mode_pass_rate_aggregates_runs(self) -> None:
        results = [
            instance("fm", "t1", False, [RunResult(1, "", [outcome("a1", verdict="pass")])]),
            instance("fm", "t2", False, [RunResult(1, "", [outcome("a1", verdict="fail")])]),
        ]
        assert failure_mode_pass_rates(results) == [{"failure_mode": "fm", "runs": 2, "passed": 1, "pass_rate": 0.5}]


class TestRunResultVerdict:
    def test_uses_aggregate_verdict(self) -> None:
        run = RunResult(1, "", [outcome("a1", verdict="pass"), outcome("a2", verdict="fail")])
        assert run.verdict == "fail"

    def test_generation_is_optional(self) -> None:
        run = RunResult(1, "out", [outcome("a1")], Generation("out", None, [], 3))
        assert run.generation is not None
        assert run.generation.turn_count == 3


class TestNextRerunId:
    def test_starts_at_one(self) -> None:
        assert next_rerun_id("t1", set()) == "t1-rerun01"

    def test_skips_taken_indexes_so_sessions_accumulate(self) -> None:
        assert next_rerun_id("t1", {"t1-rerun01", "t1-rerun02"}) == "t1-rerun03"

    def test_other_traces_do_not_shift_the_index(self) -> None:
        assert next_rerun_id("t1", {"t2-rerun01"}) == "t1-rerun01"


class TestMessageText:
    def test_plain_string_content(self) -> None:
        assert message_text(AIMessage(content="こんにちは")) == "こんにちは"

    def test_block_content_is_concatenated(self) -> None:
        message = AIMessage(content=[{"type": "text", "text": "前半"}, {"type": "text", "text": "後半"}])
        assert message_text(message) == "前半後半"

    def test_non_text_blocks_contribute_nothing(self) -> None:
        assert message_text(AIMessage(content=[{"type": "image_url", "image_url": {"url": "x"}}])) == ""


def test_format_conversation_labels_each_turn() -> None:
    history = [{"role": "assistant", "content": "問いかけ"}, {"role": "user", "content": "回答"}]
    assert format_conversation(history) == "assistant: 問いかけ\nuser: 回答"


class TestToState:
    def _trace(self, graph_state: dict[str, object]) -> SourceTrace:
        return SourceTrace(
            trace_id="t1",
            turn=3,
            meta={},
            input={
                "conversation_history": [
                    {"role": "assistant", "content": "問いかけ"},
                    {"role": "user", "content": "回答"},
                ],
                "graph_state": {"topic": "プロセス", **graph_state},
            },
            observed_output="",
        )

    def test_roles_map_to_message_types(self) -> None:
        state = to_state(self._trace({}))
        assert [type(m) for m in state["messages"]] == [AIMessage, HumanMessage]
        assert state["topic"] == "プロセス"
        assert state["turn_count"] == 3
        assert state["session_type"] == "learning"

    def test_empty_optional_fields_are_left_unset(self) -> None:
        state = to_state(self._trace({"learning_goal": None, "focus_aspects": []}))
        assert "learning_goal" not in state
        assert "focus_aspects" not in state
        assert "covered_aspects" not in state

    def test_present_optional_fields_are_carried_over(self) -> None:
        state = to_state(self._trace({"learning_goal": "理解する", "focus_aspects": ["定義"]}))
        assert state["learning_goal"] == "理解する"
        assert state["focus_aspects"] == ["定義"]


class TestSourceRecords:
    def test_every_record_is_keyed_by_id(self) -> None:
        sources = load_source_records()
        assert sources
        assert all(record["id"] == trace_id for trace_id, record in sources.items())

    def test_get_source_trace_reads_the_canonical_fields(self) -> None:
        sources = load_source_records()
        trace_id = "2026-07-14-os-process__t1"
        trace = get_source_trace(trace_id, sources)

        assert trace.trace_id == trace_id
        assert trace.observed_output == sources[trace_id]["output"]
        assert trace.input == sources[trace_id]["input"]

    def test_unknown_trace_id_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown source_trace_id"):
            get_source_trace("nope", {})
