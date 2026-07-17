from graph.coverage import format_covered_aspects, merge_coverage
from graph.output_schemas import AspectObservation
from graph.state import CoveredAspect


class TestMergeCoverage:
    def test_adds_new_aspects_preserving_order(self) -> None:
        existing: list[CoveredAspect] = [{"aspect": "信頼性", "reached_depth": "defined"}]
        observations = [
            AspectObservation(aspect="スケーラビリティ", reached_depth="mentioned"),
            AspectObservation(aspect="メンテナンス性", reached_depth="defined"),
        ]
        assert merge_coverage(existing, observations) == [
            {"aspect": "信頼性", "reached_depth": "defined"},
            {"aspect": "スケーラビリティ", "reached_depth": "mentioned"},
            {"aspect": "メンテナンス性", "reached_depth": "defined"},
        ]

    def test_promotes_depth(self) -> None:
        existing: list[CoveredAspect] = [{"aspect": "信頼性", "reached_depth": "defined"}]
        observations = [AspectObservation(aspect="信頼性", reached_depth="applied")]
        assert merge_coverage(existing, observations) == [{"aspect": "信頼性", "reached_depth": "applied"}]

    def test_never_demotes_depth(self) -> None:
        existing: list[CoveredAspect] = [{"aspect": "信頼性", "reached_depth": "exemplified"}]
        observations = [AspectObservation(aspect="信頼性", reached_depth="mentioned")]
        assert merge_coverage(existing, observations) == [{"aspect": "信頼性", "reached_depth": "exemplified"}]

    def test_empty_inputs(self) -> None:
        assert merge_coverage([], []) == []


class TestFormatCoveredAspects:
    def test_empty_returns_empty_string(self) -> None:
        assert format_covered_aspects([]) == ""

    def test_renders_depth_with_japanese_label(self) -> None:
        covered: list[CoveredAspect] = [{"aspect": "計算量", "reached_depth": "defined"}]
        assert format_covered_aspects(covered) == "- 計算量: defined（定義済み）"
