from langgraph.graph import END, StateGraph

from graph.nodes.generate_feedback import generate_feedback
from graph.nodes.generate_note import generate_note
from graph.nodes.learning_dialogue import learning_dialogue
from graph.nodes.learning_start import learning_start
from graph.state import LearningState


def route_after_dialogue(state: LearningState) -> str:
    """learning_dialogue 後に対話継続かノート生成かを判定"""
    if state["should_generate_note"]:
        return "generate_note"
    return "learning_dialogue"


def build_learning_graph(checkpointer):
    """LangGraphのStateGraphを構築してコンパイルする"""
    graph = StateGraph(LearningState)

    graph.add_node("learning_start", learning_start)
    graph.add_node("learning_dialogue", learning_dialogue)
    graph.add_node("generate_note", generate_note)
    graph.add_node("generate_feedback", generate_feedback)

    graph.set_entry_point("learning_start")

    graph.add_edge("learning_start", "learning_dialogue")

    graph.add_conditional_edges(
        "learning_dialogue",
        route_after_dialogue,
        {
            "generate_note": "generate_note",
            "learning_dialogue": "learning_dialogue",
        },
    )
    graph.add_edge("generate_note", "generate_feedback")
    graph.add_edge("generate_feedback", END)

    return graph.compile(checkpointer=checkpointer, interrupt_before=["learning_dialogue"])
