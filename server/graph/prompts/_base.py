"""プロンプト共通の定数・ヘルパー。

各プロンプトモジュールから参照される横断的な要素のみを置く。
個別タスクのプロンプト本文はタスク別モジュール側に持つ。
"""

from graph.state import TargetDepth

UNSPECIFIED_PLACEHOLDER = "未指定"

NO_FABRICATION_CHARTER = """\
- ユーザーが対話の中で実際に発言・説明した内容のみを扱う
- ユーザーが発言していない知識を推測・補完しない
- AI が説明した内容を「ユーザーが理解した」として扱わない
- ユーザーが「わかりません」と回答した場合、それは「理解していない」事実として記録する"""

TARGET_DEPTH_LABELS: dict[TargetDepth, str] = {
    "recognize": "概要を掴みたい",
    "explain": "自分の言葉で説明できるレベル",
    "apply": "実践・応用できるレベル",
}


def inject_charter(template: str) -> str:
    """`{{NO_FABRICATION}}` プレースホルダを共通の捏造禁止憲章で置換する。"""
    return template.replace("{{NO_FABRICATION}}", NO_FABRICATION_CHARTER)


def format_learning_plan_fields(
    learning_goal: str | None,
    target_depth: TargetDepth,
    focus_aspects: list[str] | None,
) -> dict[str, str]:
    """学習プラン情報を LEARNING_PLANNER_PROMPT / 質問生成プロンプトに渡す形に整形する。

    `target_depth` は必須（呼び出し側でデフォルト適用済み想定）。
    `learning_goal` / `focus_aspects` は未入力可で、その場合はプレースホルダを入れる。
    """
    if isinstance(learning_goal, str) and learning_goal.strip():
        goal_text = learning_goal.strip()
    else:
        goal_text = UNSPECIFIED_PLACEHOLDER

    depth_label = TARGET_DEPTH_LABELS[target_depth]

    if focus_aspects:
        aspects_text = "\n  - " + "\n  - ".join(focus_aspects)
    else:
        aspects_text = UNSPECIFIED_PLACEHOLDER

    return {
        "learning_goal": goal_text,
        "target_depth_label": depth_label,
        "focus_aspects": aspects_text,
    }
