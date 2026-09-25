"""学習対話 1 ターンの事前分析プロンプト（learning_dialogue の応答生成前）。

役割は 3 つ:
- 直近のユーザー発言から観点カバレッジの更新分（observations）を抽出する
- 訂正を要する誤り・混同の有無を判定する
- 応答モード（reinforce / expand / deepen）と焦点観点を決定する

誤りの判定を独立したタスクにしてあるのは、モードの一属性にしていた頃は深さだけで
モードが決まり、誤りを一度も見ないまま deepen / expand に到達できたため
（capture した 12 ターンすべてで reinforce が選ばれず error_summary が空だった）。

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
- 重視する観点: {focus_aspects}

## これまでにカバー済みの観点と到達度（過去ターン累積）
{coverage_block}

## 対話履歴（直近のみ）
{recent_messages}

## タスク
以下の順に判定する。2 を飛ばして 4 に進まない。

1. `observations`: 直近のユーザー発言で言及・説明された観点と、その発言で到達した深さ
   - mentioned=名前を挙げただけ / defined=定義を自分の言葉で述べた /
     exemplified=具体例または動作原理まで述べた / applied=応用場面・他概念との関係・トレードオフまで述べた
   - 観点名は日本語の短い名詞句にする（英語・ローマ字にしない）
   - カバー済み一覧に同じ観点があれば同じ表記を使う。表記が揺れると別観点として累積される
2. `has_misconception`: 直近のユーザー発言に、訂正を要する誤り・混同が含まれるか
   - 述べられている内容が正しいかを、深さとは別に必ず検査する
   - 誤りの例: 手段と結果の取り違え（結果として成り立つ状態を、それを実現する仕組みとして述べる）/
     問いの一部だけで全体に答える / ある概念の説明として別概念の内容を当てる /
     定義に含まれない条件を必須として述べる
   - 説明が浅い・言葉足らずなだけで、述べられている範囲は正しいものは誤りではない
3. `error_summary`: `has_misconception` が true なら、何がどう違うのかを 1 文で。false なら空文字
4. `response_mode`: 次の AI 応答のモード
   - `has_misconception` が true → 必ず reinforce
   - false のときだけ、深さで次のどちらかを選ぶ
     - deepen: 直近の説明が単一観点で到達目標に届いていない
     - expand: 直近の説明が十分。複数観点が一度に列挙され各観点に最低限の定義があれば、
       個々の観点が defined 止まりでも expand を優先する（焦点観点への質問の深さはモード C の基準で決める）
   - 到達目標は exemplified（具体例または動作原理まで述べた）
5. `selected_aspect`: 次の応答で焦点を当てる観点を 1 つ
   - reinforce のときは、誤りを含む観点を選ぶ
   - それ以外の選定基準: 重視する観点の未カバー項目 > 到達度が到達目標に最も届いていない既出観点 > 既出順
   - 日本語の短い名詞句で、`observations` やカバー済み一覧と同じ表記を使う

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
