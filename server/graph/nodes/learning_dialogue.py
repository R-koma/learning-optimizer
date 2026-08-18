from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from graph.coverage import merge_coverage
from graph.llm import llm
from graph.multimodal import load_image_blocks
from graph.nodes._turn_analysis import analyze_dialogue_turn
from graph.output_schemas import DialogueTurnAnalysis
from graph.prompts import build_question_prompt, classify_user_intent, format_learning_plan_fields
from graph.prompts.question import PROMPT_FINGERPRINT, PROMPT_VERSION
from graph.state import CoveredAspect, LearningState, TurnAnalysisRecord
from storage import get_storage


def _to_record(analysis: DialogueTurnAnalysis | None) -> TurnAnalysisRecord | None:
    """プロンプトに注入された決定内容だけを state 保存用に抜き出す。"""
    if analysis is None:
        return None
    return TurnAnalysisRecord(
        response_mode=analysis.response_mode,
        selected_aspect=analysis.selected_aspect,
        error_summary=analysis.error_summary,
    )


async def learning_dialogue(state: LearningState) -> dict[str, Any]:
    """対話継続: ファシリテーターとして説明を促す（評価はしない）。

    dialogue intent のターンでは応答生成の前に事前分析（turn_analysis）を 1 回行い、
    観点カバレッジの更新と応答モードの決定をする。事前分析が失敗しても
    ターンは止めず、モード自己判定のプロンプトへフォールバックする。

    決定内容（response_mode / selected_aspect）は state に残す。プロンプトを変える値なので、
    これが無いと会話履歴と state からターンを再現できない（eval の regression 実行で使う）。

    学習セッションはユーザーの明示的な終了操作で完了するため、このノードは
    終了判定を持たず、`should_generate_note` は常に False を返す。
    （終了スイッチは api/websocket/chat.py の `_handle_end_session` が外部から立てる）
    """
    recent_messages = "\n".join(
        f"{'ユーザー' if msg.type == 'human' else 'AI'}: {msg.content}" for msg in state["messages"][-6:]
    )
    plan_fields = format_learning_plan_fields(
        learning_goal=state.get("learning_goal"),
        focus_aspects=state.get("focus_aspects"),
    )

    covered_aspects: list[CoveredAspect] = list(state.get("covered_aspects") or [])
    turn_analysis: DialogueTurnAnalysis | None = None
    if classify_user_intent(state["messages"]) == "dialogue":
        turn_analysis = await analyze_dialogue_turn(
            state,
            recent_messages=recent_messages,
            plan_fields=plan_fields,
            covered_aspects=covered_aspects,
        )
        if turn_analysis is not None:
            covered_aspects = merge_coverage(covered_aspects, turn_analysis.observations)

    question_prompt, intent = build_question_prompt(
        topic=state["topic"],
        recent_messages=recent_messages,
        plan_fields=plan_fields,
        messages=state["messages"],
        covered_aspects=covered_aspects,
        turn_analysis=turn_analysis,
    )
    llm_messages: list[BaseMessage] = [SystemMessage(content=question_prompt)]
    if state["messages"]:
        image_blocks = await load_image_blocks(state["messages"][-1], get_storage())
        if image_blocks:
            llm_messages.append(HumanMessage(content=image_blocks))

    response = await llm.ainvoke(
        llm_messages,
        config={
            "metadata": {
                "prompt_version": PROMPT_VERSION,
                "prompt_fingerprint": PROMPT_FINGERPRINT,
                "intent": intent,
                "response_mode": turn_analysis.response_mode if turn_analysis else None,
                "selected_aspect": turn_analysis.selected_aspect if turn_analysis else None,
            }
        },
    )

    return {
        "messages": [response],
        "turn_count": state["turn_count"] + 1,
        "should_generate_note": False,
        "covered_aspects": covered_aspects,
        "turn_analysis": _to_record(turn_analysis),
    }
