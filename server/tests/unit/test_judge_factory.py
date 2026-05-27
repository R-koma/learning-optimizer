"""evals._judge_factory.build_judge_llm の provider 分岐テスト。"""

from __future__ import annotations

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from evals._judge_factory import build_judge_llm


def test_default_returns_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EVALS_JUDGE_PROVIDER", raising=False)
    monkeypatch.delenv("EVALS_JUDGE_MODEL", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-anthropic")

    judge = build_judge_llm()

    assert isinstance(judge, ChatAnthropic)
    assert judge.model == "claude-sonnet-4-6"


def test_openai_provider_returns_chat_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVALS_JUDGE_PROVIDER", "openai")
    monkeypatch.setenv("EVALS_JUDGE_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")

    judge = build_judge_llm()

    assert isinstance(judge, ChatOpenAI)
    assert judge.model_name == "gpt-4o-mini"


def test_anthropic_without_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVALS_JUDGE_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        build_judge_llm()


def test_openai_without_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVALS_JUDGE_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_judge_llm()


def test_unknown_provider_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVALS_JUDGE_PROVIDER", "gemini")

    with pytest.raises(ValueError, match="unknown EVALS_JUDGE_PROVIDER"):
        build_judge_llm()
