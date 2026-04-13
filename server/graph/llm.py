from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

llm: ChatOpenAI = ChatOpenAI(model="gpt-4.1-nano", temperature=0.7)  # type: ignore[call-arg]
llm_structured: ChatOpenAI = ChatOpenAI(model="gpt-4.1-nano", temperature=0)  # type: ignore[call-arg]
