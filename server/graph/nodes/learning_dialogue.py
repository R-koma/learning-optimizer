from typing import Any

from langchain_core.messages import SystemMessage

from graph.nodes._dialogue import invoke_dialogue_llm
from graph.prompts import build_question_prompt, format_learning_plan_fields
from graph.state import LearningState


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
    response = await invoke_dialogue_llm(
        state,
        [SystemMessage(content=question_prompt)],
        "learning_dialogue",
    )

    return {
        "messages": [response],
        "turn_count": state["turn_count"] + 1,
        "should_generate_note": False,
    }
