"""Thin wrapper around the OpenAI SDK pointed at LM Studio's local server.

LM Studio exposes an OpenAI-compatible REST API once its local server is
running (`lms server start`, or Developer tab -> Start Server in the app).
Talking to it is identical to talking to OpenAI's API except for base_url —
the api_key is required by the SDK but ignored by LM Studio.
"""

from __future__ import annotations

import json
import re

from openai import APIConnectionError, OpenAI

from app.config import settings

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=settings.lm_studio_base_url,
            api_key=settings.lm_studio_api_key,
            timeout=settings.request_timeout_seconds,
        )
    return _client


def list_models() -> list[str]:
    """Raises APIConnectionError if LM Studio's server isn't running."""
    return [m.id for m in get_client().models.list().data]


def is_server_reachable() -> bool:
    try:
        list_models()
        return True
    except APIConnectionError:
        return False


_FENCE_RE = re.compile(r"^```[\w+-]*\n(.*?)\n```$", re.DOTALL)


def _strip_code_fences(text: str) -> str:
    """Strip a single wrapping ```lang ... ``` fence, if the whole response is one.
    Handles any language tag (```json, ```python, ```svelte, bare ```, etc.) —
    models reliably wrap output in fences even when told not to.
    """
    text = text.strip()
    match = _FENCE_RE.match(text)
    return match.group(1) if match else text


def chat_json(system_prompt: str, user_prompt: str, model: str | None = None) -> dict:
    """Send a chat completion and parse the response as JSON.

    Tries LM Studio's JSON-object response mode first (widely supported by the
    llama.cpp-backed runtimes LM Studio uses); falls back to parsing raw text
    and stripping markdown code fences if the server/model doesn't honour it.
    Raises json.JSONDecodeError if the model's output still isn't valid JSON —
    callers should catch this and retry via build_repair_prompt (see c4_service.py).
    """
    client = get_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = client.chat.completions.create(
            model=model or settings.lm_studio_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.2,
        )
    except Exception:
        # Model/runtime doesn't support response_format — retry without it.
        response = client.chat.completions.create(
            model=model or settings.lm_studio_model,
            messages=messages,
            temperature=0.2,
        )

    raw = response.choices[0].message.content or ""
    return json.loads(_strip_code_fences(raw))


def chat_text(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    """Send a chat completion and return the raw text response, with a single
    wrapping markdown code fence stripped if the whole response is one.
    Used for free-form content/file generation, as opposed to chat_json's
    structured-data extraction (see scripts/generate_file.py).
    """
    client = get_client()
    response = client.chat.completions.create(
        model=model or settings.lm_studio_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    raw = response.choices[0].message.content or ""
    return _strip_code_fences(raw)
