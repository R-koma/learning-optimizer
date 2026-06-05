from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from graph.multimodal import load_image_blocks
from graph.nodes._dialogue import invoke_dialogue_llm
from graph.prompts import build_question_prompt, format_learning_plan_fields
from graph.state import LearningState
from storage import get_storage


async def learning_dialogue(state: LearningState) -> dict[str, Any]:
    """対話継続: ファシリテーターとして説明を促す（評価はしない）。

    学習セッションはユーザーの明示的な終了操作で完了するため、このノードは
    終了判定を持たず、`should_generate_note` は常に False を返す。
    （終了スイッチは api/websocket/chat.py の `_handle_end_session` が外部から立てる）
    """
    recent_messages = "\n".join(
        f"{'ユーザー' if msg.type == 'human' else 'AI'}: {msg.content}" for msg in state["messages"][-6:]
    )
    plan_fields = format_learning_plan_fields(
        learning_goal=state.get("learning_goal"),
        target_depth=state.get("target_depth") or "recognize",
        focus_aspects=state.get("focus_aspects"),
    )
    question_prompt, _intent = build_question_prompt(
        topic=state["topic"],
        recent_messages=recent_messages,
        plan_fields=plan_fields,
        messages=state["messages"],
    )
    # 会話履歴はプロンプト本文に文字列で埋め込まれるため、画像は最新メッセージ分のみ
    # 画像ブロックとして別途 LLM に渡す。
    llm_messages: list[BaseMessage] = [SystemMessage(content=question_prompt)]
    if state["messages"]:
        image_blocks = await load_image_blocks(state["messages"][-1], get_storage())
        if image_blocks:
            llm_messages.append(HumanMessage(content=image_blocks))

    response = await invoke_dialogue_llm(
        state,
        llm_messages,
        "learning_dialogue",
    )

    return {
        "messages": [response],
        "turn_count": state["turn_count"] + 1,
        "should_generate_note": False,
    }
