"""Compatibility facade over per-agent LLMHub adapters.

Prefer ``app.llmhub_adapter.get_adapter(agent_id)`` for new code. This module
keeps older call sites (``c4_service``, scripts) working against the medium
tier model configured in ``config/llmhub.yaml``.
"""

from __future__ import annotations

from app.llmhub_adapter import get_adapter, is_hub_reachable, list_models

__all__ = [
    "chat_json",
    "chat_text",
    "is_server_reachable",
    "list_models",
]


def chat_json(system_prompt: str, user_prompt: str, model: str | None = None) -> dict:
    return get_adapter("subagent-context").chat_json(
        system_prompt, user_prompt, model=model
    )


def chat_text(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    return get_adapter("c4-doc-agent").chat_text(
        system_prompt, user_prompt, model=model, temperature=temperature
    )


def is_server_reachable() -> bool:
    return is_hub_reachable()
