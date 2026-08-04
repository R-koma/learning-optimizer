"""学習対話 1 ターンの事前分析プロンプト（learning_dialogue の応答生成前）。

役割は 2 つ:
- 直近のユーザー発言から観点カバレッジの更新分（observations）を抽出する
- 応答モード（reinforce / expand / deepen）と焦点観点を決定する

判定を応答生成プロンプト内の暗黙判断から分離することで、モード選択を
トレース・eval 可能にし、生成プロンプトには該当モードの指示だけを載せる。
"""

from collections.abc import Sequence

from graph.coverage import format_covered_aspects
from graph.prompts._base import inject_charter
from graph.state import CoveredAspect

TURN_ANALYSIS_PROMPT = inject_charter(
    """\
あなたは学習対話の 1 ターンを分析する専門家です。
ユーザーが「{topic}」について自分の言葉で説明しています。
直近のユーザー発言を分析し、DialogueTurnAnalysis スキーマに従って構造化して出力してください。

## 学習プラン
- 学習ゴール: {learning_goal}
- 到達したいレベル: {target_depth_label}
- 重視する観点: {focus_aspects}

## これまでにカバー済みの観点と到達度（過去ターン累積）
{coverage_block}

## 対話履歴（直近のみ）
{recent_messages}

## タスク
1. `observations`: 直近のユーザー発言で言及・説明された観点と、その発言で到達した深さ
   - mentioned=名前を挙げただけ / defined=定義を自分の言葉で述べた /
     exemplified=具体例または動作原理まで述べた / applied=応用場面・他概念との関係・トレードオフまで述べた
   - 観点名は日本語の短い名詞句にする（英語・ローマ字にしない）
   - カバー済み一覧に同じ観点があれば同じ表記を使う。表記が揺れると別観点として累積される
2. `response_mode`: 次の AI 応答のモード
   - reinforce: ユーザーの説明に明確な誤り・重大な混同がある場合のみ。
     深さが「到達したいレベル」に足りないだけの正確な説明は誤りではない
   - deepen: 誤りはないが、直近の説明が単一観点で「到達したいレベル」に届いていない
   - expand: 誤りがなく、直近の説明が十分（複数観点の一括列挙で各観点に最低限の定義がある場合を含む）
   - 「到達したいレベル」と到達度の対応: 概要を掴みたい=defined で十分 /
     自分の言葉で説明できるレベル=exemplified まで / 実践・応用できるレベル=applied まで
3. `selected_aspect`: 次の応答で焦点を当てる観点を 1 つ
   - 選定基準: 重視する観点の未カバー項目 > 到達度が「到達したいレベル」に最も届いていない既出観点 > 既出順
   - 日本語の短い名詞句で、`observations` やカバー済み一覧と同じ表記を使う
4. `error_summary`: reinforce の場合のみ誤りの内容を 1 文で。それ以外は空文字

## 厳守事項
{{NO_FABRICATION}}
"""
)

_EMPTY_COVERAGE_PLACEHOLDER = "（まだなし）"


def build_turn_analysis_prompt(
    *,
    topic: str,
    recent_messages: str,
    plan_fields: dict[str, str],
    covered_aspects: Sequence[CoveredAspect],
) -> str:
    coverage_block = format_covered_aspects(covered_aspects) or _EMPTY_COVERAGE_PLACEHOLDER
    return TURN_ANALYSIS_PROMPT.format(
        topic=topic,
        recent_messages=recent_messages,
        coverage_block=coverage_block,
        **plan_fields,
    )
