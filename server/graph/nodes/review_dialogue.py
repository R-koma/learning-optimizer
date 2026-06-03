from typing import Any

from langchain_core.messages import SystemMessage

from graph.nodes._dialogue import invoke_dialogue_llm
from graph.prompts import REVIEW_SYSTEM_PROMPT
from graph.state import LearningState

# REVIEW_SYSTEM_PROMPT が「対話を終える」と判断したときに LLM が出力する
# リテラル。値はプロンプト本文（graph/prompts/review.py）の指示と一致させる。
REVIEW_END_SIGNAL = "LEARNING_END"


async def review_dialogue(state: LearningState) -> dict[str, Any]:
    """復習対話の継続。LLM が REVIEW_END_SIGNAL を返したら復習更新へ進む。

    学習セッションと異なり、終了判定は LLM が主体的に行う（自走終了）。
    """
    prompt = REVIEW_SYSTEM_PROMPT.format(
        topic=state["topic"],
        content=state.get("note_content", ""),
        summary=state.get("note_summary", ""),
    )
    messages = [SystemMessage(content=prompt), *state["messages"]]
    response = await invoke_dialogue_llm(state, messages, "review_dialogue")

    content = response.content
    should_generate_note = isinstance(content, str) and content.strip() == REVIEW_END_SIGNAL

    return {
        "messages": [response],
        "turn_count": state["turn_count"] + 1,
        "should_generate_note": should_generate_note,
    }
