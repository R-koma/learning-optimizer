import pytest

from evals.golden.checks import CheckContext, available_checks, run_check


def _ctx(output: str, *, recent: tuple[str, ...] = (), **params: object) -> CheckContext:
    return CheckContext(output=output, recent_system_questions=recent, parameters=params)


class TestEndsWithQuestionMark:
    @pytest.mark.parametrize("text", ["これは何ですか？", "what is this?", "...ですか？  \n"])
    def test_holds_true(self, text: str) -> None:
        assert run_check("ends_with_question_mark", _ctx(text)).holds is True

    @pytest.mark.parametrize("text", ["これは説明です。", "no question here", "？の途中で終わる文"])
    def test_holds_false(self, text: str) -> None:
        assert run_check("ends_with_question_mark", _ctx(text)).holds is False


class TestContainsAnyPhrase:
    def test_matches_phrase(self) -> None:
        phrase = "他に触れておきたい観点があれば"
        out = run_check("contains_any_phrase", _ctx(f"{phrase}どうぞ。", phrases=[phrase]))
        assert out.holds is True

    def test_no_match(self) -> None:
        ctx = _ctx("次はこの点を考えましょう。", phrases=["他に触れておきたい観点があれば"])
        assert run_check("contains_any_phrase", ctx).holds is False

    def test_missing_phrases_param_raises(self) -> None:
        with pytest.raises(ValueError, match="phrases"):
            run_check("contains_any_phrase", _ctx("text"))


class TestParaphrasesRecentQuestion:
    def test_identical_is_paraphrase(self) -> None:
        q = "信頼性について具体的な場面を考えてみませんか？"
        out = run_check("paraphrases_recent_question", _ctx(q, recent=(q,), threshold=0.6))
        assert out.holds is True

    def test_unrelated_is_not_paraphrase(self) -> None:
        out = run_check(
            "paraphrases_recent_question",
            _ctx("RAID 以外のフォールトには何がありますか？", recent=("好きな食べ物は何ですか？",), threshold=0.6),
        )
        assert out.holds is False

    def test_threshold_controls_decision(self) -> None:
        out = "信頼性の具体例を一つ挙げてみてください。"
        recent = ("信頼性の具体例を挙げてみましょう。",)
        assert run_check("paraphrases_recent_question", _ctx(out, recent=recent, threshold=0.99)).holds is False
        assert run_check("paraphrases_recent_question", _ctx(out, recent=recent, threshold=0.1)).holds is True

    def test_no_recent_questions_is_false(self) -> None:
        out = run_check("paraphrases_recent_question", _ctx("何かありますか？", recent=(), threshold=0.6))
        assert out.holds is False


class TestRegistry:
    def test_unknown_check_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown deterministic check"):
            run_check("does_not_exist", _ctx("x"))

    def test_available_checks_listed(self) -> None:
        names = available_checks()
        assert "ends_with_question_mark" in names
        assert "contains_any_phrase" in names
        assert "paraphrases_recent_question" in names
