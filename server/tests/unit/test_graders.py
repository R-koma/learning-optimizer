from evals.graders import (
    dialogue_ended_correctly,
    feedback_is_actionable,
    note_has_sections,
    response_label_match,
)
from graph.output_schemas import FeedbackOutput


class TestNoteHasSections:
    def test_all_required_present_with_callout(self) -> None:
        content = "リード段落です。\n\n## 学んだこと\n- y\n\n## 重要なポイント\n- z\n\n> **まだ曖昧な点**\n> - w"
        result = note_has_sections.grade(content)
        assert result.passed is True
        assert result.score == 1.0
        assert result.metadata["has_ambiguity_callout"] is True

    def test_all_required_present_without_callout(self) -> None:
        content = "リード段落です。\n\n## 学んだこと\n- y\n\n## 重要なポイント\n- z"
        result = note_has_sections.grade(content)
        assert result.passed is True
        assert result.score == 1.0
        assert result.metadata["has_ambiguity_callout"] is False

    def test_one_h2_missing(self) -> None:
        content = "リード段落です。\n\n## 学んだこと\n- y"
        result = note_has_sections.grade(content)
        assert result.passed is False
        assert result.score == 0.5
        assert "重要なポイント" in result.reason

    def test_all_h2_missing(self) -> None:
        content = "Some random text without any section"
        result = note_has_sections.grade(content)
        assert result.passed is False
        assert result.score == 0.0


class TestFeedbackIsActionable:
    def test_full_feedback(self) -> None:
        fb = FeedbackOutput(
            understanding_level="medium",
            strength=["デコレータの基本構造を理解できています"],
            improvement_points=["クロージャとの関係を整理しましょう"],
        )
        result = feedback_is_actionable.grade(fb)
        assert result.passed is True
        assert result.score == 1.0

    def test_missing_improvement_points(self) -> None:
        fb = FeedbackOutput(
            understanding_level="high",
            strength=["デコレータの基本構造を理解できています"],
            improvement_points=[],
        )
        result = feedback_is_actionable.grade(fb)
        assert result.passed is False
        assert result.score == 0.5
        assert "improvement_points" in result.reason

    def test_missing_both(self) -> None:
        fb = FeedbackOutput(understanding_level="low", strength=[], improvement_points=[])
        result = feedback_is_actionable.grade(fb)
        assert result.passed is False
        assert result.score == 0.0


class TestDialogueEndedCorrectly:
    def test_learning_end_signal(self) -> None:
        result = dialogue_ended_correctly.grade(response_content="LEARNING_END", expected_label="LEARNING_END")
        assert result.passed is True
        assert result.score == 1.0

    def test_learning_end_with_extra_text_fails(self) -> None:
        result = dialogue_ended_correctly.grade(
            response_content="お疲れ様でした！LEARNING_END", expected_label="LEARNING_END"
        )
        assert result.passed is False
        assert result.score == 0.0

    def test_continue_with_question(self) -> None:
        result = dialogue_ended_correctly.grade(
            response_content="他には何を覚えていますか？", expected_label="CONTINUE"
        )
        assert result.passed is True
        assert result.score == 1.0

    def test_continue_but_got_learning_end(self) -> None:
        result = dialogue_ended_correctly.grade(response_content="LEARNING_END", expected_label="CONTINUE")
        assert result.passed is False
        assert result.score == 0.0

    def test_unknown_label(self) -> None:
        result = dialogue_ended_correctly.grade(response_content="x", expected_label="UNKNOWN")
        assert result.passed is False


class TestResponseLabelMatch:
    def test_match_learning_end(self) -> None:
        result = response_label_match.grade(response_content="LEARNING_END", expected_label="LEARNING_END")
        assert result.passed is True
        assert result.score == 1.0
        assert result.metadata["actual_label"] == "LEARNING_END"

    def test_match_continue(self) -> None:
        result = response_label_match.grade(response_content="他には何を覚えていますか？", expected_label="CONTINUE")
        assert result.passed is True
        assert result.score == 1.0
        assert result.metadata["actual_label"] == "CONTINUE"

    def test_mismatch(self) -> None:
        result = response_label_match.grade(response_content="LEARNING_END", expected_label="CONTINUE")
        assert result.passed is False
        assert result.score == 0.0

    def test_predict_label_with_whitespace(self) -> None:
        assert response_label_match.predict_label("  LEARNING_END  ") == "LEARNING_END"
        assert response_label_match.predict_label("LEARNING_END\n") == "LEARNING_END"
        assert response_label_match.predict_label("質問です？") == "CONTINUE"
