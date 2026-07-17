from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

llm: ChatOpenAI = ChatOpenAI(model="gpt-4.1-nano", temperature=0.7)  # type: ignore[call-arg]
llm_structured: ChatOpenAI = ChatOpenAI(model="gpt-5-nano", temperature=0)  # type: ignore[call-arg]

# ストリーミング対象ノード内で行う内部 LLM 呼び出し（structured output 等）に付けるタグ。
# WebSocket 側はこのタグ付きチャンクをクライアントへ流さない（api/websocket/chat.py 参照）
INTERNAL_LLM_TAG = "internal-llm"
