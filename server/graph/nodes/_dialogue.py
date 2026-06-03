"""対話ノード共通の機構（LLM 呼び出し + trace 計測）。

learning / review の対話ノードは「どのプロンプト・どのメッセージ列を渡すか」
（ポリシー）が異なるが、「LLM を計測付きで呼ぶ」（機構）は共通。後者をここに
集約し、各ノードはポリシーのみを持つようにする。
"""

from langchain_core.messages import BaseMessage

from graph.llm import llm
from graph.state import LearningState
from observability.llm import measured_ainvoke
from observability.tracing import build_trace_context


async def invoke_dialogue_llm(
    state: LearningState,
    messages: list[BaseMessage],
    node_name: str,
) -> BaseMessage:
    response: BaseMessage = await measured_ainvoke(
        runnable=llm,
        messages=messages,
        context=build_trace_context(state),
        node_name=node_name,
    )
    return response
