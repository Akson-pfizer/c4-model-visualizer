"""Per-agent Pfizer LLMHub adapters (OpenAI-compatible chat/completions).

Each agent in the C4 pipeline receives its own ``LLMHubAdapter`` instance,
bound to a model tier from ``config/llmhub.yaml``:

- **powerful** — Manager / Supervisor / Documentation agents
- **medium** — Context / Container / Component / Code specialist subagents

Endpoints follow https://docs.platforms.pfizer/llmhub/docs/llmhub-endpoints
(``GET /v1/models``, ``POST /v1/chat/completions``). Auth is Bearer token plus
a non-empty ``User-Agent`` (LLMHub rejects UA-less machine traffic).
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache

from openai import APIConnectionError, APIStatusError, OpenAI

from app.config import AgentAdapterConfig, settings

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^```[\w+-]*\n(.*?)\n```$", re.DOTALL)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    match = _FENCE_RE.match(text)
    return match.group(1) if match else text


def _normalize_base_url(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    for suffix in ("/chat/completions", "/completions", "/models"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].rstrip("/")
    if not cleaned.endswith("/v1"):
        cleaned = f"{cleaned}/v1"
    return cleaned


class LLMHubAdapter:
    """OpenAI-SDK client pointed at Pfizer LLMHub for one agent role."""

    def __init__(self, agent_config: AgentAdapterConfig) -> None:
        self.agent_id = agent_config.agent_id
        self.tier = agent_config.tier
        self.model = agent_config.model
        self.experience_db = agent_config.experience_db
        self._client: OpenAI | None = None

    @property
    def base_url(self) -> str:
        return _normalize_base_url(settings.llmhub_base_url)

    def _get_client(self) -> OpenAI:
        if self._client is None:
            if not settings.llmhub_api_key:
                raise RuntimeError(
                    "LLMHUB_API_KEY is not configured. Set it in config/llmhub.yaml "
                    "or the LLMHUB_API_KEY environment variable."
                )
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=settings.llmhub_api_key,
                timeout=settings.request_timeout_seconds,
                default_headers={"User-Agent": settings.llmhub_user_agent},
            )
        return self._client

    def list_models(self) -> list[str]:
        """Raise APIConnectionError / auth errors if LLMHub is unreachable."""
        return [m.id for m in self._get_client().models.list().data]

    def is_reachable(self) -> bool:
        if not settings.llmhub_api_key:
            return False
        try:
            self.list_models()
            return True
        except (APIConnectionError, APIStatusError, RuntimeError) as exc:
            logger.debug("[%s] LLMHub unreachable: %s", self.agent_id, exc)
            return False

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> dict:
        """Chat completion parsed as JSON (with markdown-fence strip fallback)."""
        client = self._get_client()
        target_model = model or self.model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = client.chat.completions.create(
                model=target_model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
            )
        except Exception:
            # Some gateway models reject response_format — retry without it.
            response = client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
            )

        raw = response.choices[0].message.content or ""
        return json.loads(_strip_code_fences(raw))

    def chat_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=model or self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        raw = response.choices[0].message.content or ""
        return _strip_code_fences(raw)


@lru_cache(maxsize=32)
def get_adapter(agent_id: str) -> LLMHubAdapter:
    """Return (and cache) the LLMHub adapter bound to ``agent_id``."""
    return LLMHubAdapter(settings.adapter_config(agent_id))


def is_hub_reachable() -> bool:
    """Cheap reachability probe using the Manager adapter."""
    return get_adapter("c4-manager").is_reachable()


def list_models() -> list[str]:
    return get_adapter("c4-manager").list_models()


_NON_CHAT_MARKERS = (
    "embedding",
    "embed",
    "whisper",
    "tts",
    "audio",
    "dall-e",
    "dalle",
    "gpt-image",
    "image-1",
    "moderation",
    "transcribe",
    "realtime",
)


def is_chat_model(model_id: str) -> bool:
    """True for chat/completions models; false for embeddings, image, audio, etc."""
    mid = (model_id or "").strip().lower()
    if not mid:
        return False
    return not any(marker in mid for marker in _NON_CHAT_MARKERS)


def filter_chat_models(model_ids: list[str]) -> list[str]:
    """Keep only chat-capable model IDs, preserving order and uniqueness."""
    seen: set[str] = set()
    out: list[str] = []
    for mid in model_ids:
        name = str(mid).strip()
        if not name or name in seen or not is_chat_model(name):
            continue
        seen.add(name)
        out.append(name)
    return out


def list_chat_models() -> list[str]:
    return filter_chat_models(list_models())
