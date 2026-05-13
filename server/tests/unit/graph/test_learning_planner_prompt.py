from graph.prompts import LEARNING_PLANNER_PROMPT, format_learning_plan_fields


def _render(
    *,
    topic: str = "データシステムの基礎",
    learning_goal: str | None = None,
    target_depth: str = "recognize",
    focus_aspects: list[str] | None = None,
) -> str:
    fields = format_learning_plan_fields(
        learning_goal=learning_goal,
        target_depth=target_depth,  # type: ignore[arg-type]
        focus_aspects=focus_aspects,
    )
    return LEARNING_PLANNER_PROMPT.format(topic=topic, **fields)


class TestLearningPlannerPromptRendering:
    def test_skip_instruction_present_when_all_unspecified(self) -> None:
        rendered = _render()
        assert "両方とも「未指定」なら" in rendered
        assert "両方未指定ならスキップ" in rendered

    def test_fabrication_warning_with_bad_example_present(self) -> None:
        rendered = _render()
        assert "❌" in rendered
        assert "捏造" in rendered
        assert "既にお伝えいただいた内容から" in rendered

    def test_ui_selection_note_present(self) -> None:
        rendered = _render()
        assert "UI 選択値" in rendered

    def test_topic_is_interpolated(self) -> None:
        rendered = _render(topic="クロージャ")
        assert "クロージャ" in rendered

    def test_learning_goal_text_appears_when_specified(self) -> None:
        rendered = _render(learning_goal="業務で Postgres を理解したい")
        assert "業務で Postgres を理解したい" in rendered

    def test_unspecified_placeholder_appears_when_omitted(self) -> None:
        rendered = _render(learning_goal=None, focus_aspects=None)
        # 学習ゴール: 未指定 / 重視する観点: 未指定 が両方レンダリングされる
        assert "学習ゴール: 未指定" in rendered
        assert "重視する観点: 未指定" in rendered
