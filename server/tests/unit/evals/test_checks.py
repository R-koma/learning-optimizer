import pytest

from evals.checks import contains_generic_prompt_phrase, run_check


class TestContainsGenericPromptPhrase:
    def test_detects_known_phrase(self) -> None:
        result = contains_generic_prompt_phrase("さらに詳しく説明してみてください。")
        assert result.holds is True

    def test_no_match_returns_false(self) -> None:
        result = contains_generic_prompt_phrase("スループットについて、もう一度説明してもらえますか？")
        assert result.holds is False

    def test_detail_lists_matched_phrases(self) -> None:
        result = contains_generic_prompt_phrase("もう少し詳しく、さらに詳しく教えてください")
        assert "もう少し詳しく" in result.detail
        assert "さらに詳しく" in result.detail


class TestRunCheck:
    def test_dispatches_by_name(self) -> None:
        result = run_check("contains_generic_prompt_phrase", "掘り下げてみませんか？")
        assert result.holds is True

    def test_unknown_check_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown deterministic check"):
            run_check("does_not_exist", "output")
