"""LLM-as-judge 用モデルを provider 切替できる factory。

生成側 LLM（gpt-4o）と judge LLM を分離するための単一エントリポイント。
provider / model は EVALS_JUDGE_PROVIDER / EVALS_JUDGE_MODEL env で切替可能。

未設定時のデフォルトは anthropic / claude-sonnet-4-6（生成側 OpenAI と provider レベルで分離して
self-preference bias を排除する）。

呼び出し側は ChatOpenAI 固有 API に依存してはならない。返り値は BaseChatModel として扱う。
"""

from __future__ import annotations

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL_BY_PROVIDER: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o",
}


def build_judge_llm(*, temperature: float = 0.0) -> BaseChatModel:
    """env 設定に従って judge 用 ChatModel を生成する。

    env vars:
        EVALS_JUDGE_PROVIDER: "anthropic" | "openai" (default: "anthropic")
        EVALS_JUDGE_MODEL: モデル ID（未指定なら provider 既定）

    Raises:
        RuntimeError: 必要な API キーが未設定の場合。
        ValueError: 未知の provider が指定された場合。
    """
    provider = os.getenv("EVALS_JUDGE_PROVIDER", DEFAULT_PROVIDER).lower()
    if provider not in DEFAULT_MODEL_BY_PROVIDER:
        raise ValueError(f"unknown EVALS_JUDGE_PROVIDER: {provider!r} (expected 'anthropic' or 'openai')")
    model = os.getenv("EVALS_JUDGE_MODEL") or DEFAULT_MODEL_BY_PROVIDER[provider]

    if provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required when EVALS_JUDGE_PROVIDER=anthropic. "
                "Set it in .env or switch EVALS_JUDGE_PROVIDER=openai."
            )
        return ChatAnthropic(model=model, temperature=temperature)

    # provider == "openai"
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required when EVALS_JUDGE_PROVIDER=openai.")
    return ChatOpenAI(model=model, temperature=temperature)  # type: ignore[call-arg]
