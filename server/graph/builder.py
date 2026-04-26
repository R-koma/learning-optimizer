from typing import Any

from langgraph.graph import END, StateGraph

from graph.nodes.generate_feedback import generate_feedback
from graph.nodes.generate_note import generate_note
from graph.nodes.learning_dialogue import learning_dialogue
from graph.nodes.learning_start import learning_start
from graph.nodes.update_note_and_feedback import update_note_and_feedback
from graph.state import LearningState


def route_after_dialogue(state: LearningState) -> str:
    """learning_dialogue 後に対話継続かノート生成/復習更新かを判定"""
    if not state["should_generate_note"]:
        return "learning_dialogue"
    if state.get("session_type") == "review":
        return "update_note_and_feedback"
    return "generate_note"


def build_learning_graph(checkpointer: Any) -> Any:
    """LangGraphのStateGraphを構築してコンパイルする"""
    graph = StateGraph(LearningState)

    graph.add_node("learning_start", learning_start)
    graph.add_node("learning_dialogue", learning_dialogue)
    graph.add_node("generate_note", generate_note)
    graph.add_node("generate_feedback", generate_feedback)
    graph.add_node("update_note_and_feedback", update_note_and_feedback)

    graph.set_entry_point("learning_start")

    graph.add_edge("learning_start", "learning_dialogue")

    graph.add_conditional_edges(
        "learning_dialogue",
        route_after_dialogue,
        {
            "generate_note": "generate_note",
            "update_note_and_feedback": "update_note_and_feedback",
            "learning_dialogue": "learning_dialogue",
        },
    )
    graph.add_edge("generate_note", "generate_feedback")
    graph.add_edge("generate_feedback", END)
    graph.add_edge("update_note_and_feedback", END)

    return graph.compile(checkpointer=checkpointer, interrupt_before=["learning_dialogue"])
