from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

load_dotenv()

llm: ChatOpenAI = ChatOpenAI(model="gpt-4.1-nano", temperature=0.7)  # type: ignore[call-arg]
llm_structured: ChatOpenAI = ChatOpenAI(model="gpt-5-nano", temperature=0)  # type: ignore[call-arg]
llm_judge: ChatAnthropic = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
# llm_judge: ChatAnthropic = ChatAnthropic(model="claude-opus-5")

INTERNAL_LLM_TAG = "internal-llm"
