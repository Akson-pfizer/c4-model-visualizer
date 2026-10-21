"""Settings loaded from ``config/llmhub.yaml`` with environment overrides.

Pfizer LLMHub credentials and per-agent model tiers live in the YAML config.
Environment variables always win over file values for secrets and runtime knobs.
See: https://docs.platforms.pfizer/llmhub/docs/llmhub-endpoints
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG_PATH = _BACKEND_ROOT / "config" / "llmhub.yaml"
_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _resolve_env_placeholders(value: Any) -> Any:
    """Replace ``${VAR}`` placeholders with environment values (empty if unset)."""
    if isinstance(value, dict):
        return {k: _resolve_env_placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_placeholders(v) for v in value]
    if isinstance(value, str):
        def _replace(match: re.Match[str]) -> str:
            return os.getenv(match.group(1), "")

        return _ENV_PATTERN.sub(_replace, value)
    return value


def _load_yaml_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return _resolve_env_placeholders(raw)


@dataclass(frozen=True)
class AgentAdapterConfig:
    agent_id: str
    tier: str  # "powerful" | "medium"
    model: str
    experience_db: Path | None = None


@dataclass
class Settings:
    """Runtime settings for the C4 multi-agent backend."""

    llmhub_base_url: str = "https://llmhub.platforms.pfizer/v1"
    llmhub_api_key: str = ""
    llmhub_user_agent: str = "c4-model-visualizer/1.0"
    request_timeout_seconds: float = 120.0

    model_powerful: str = "gpt-4o"
    model_medium: str = "gpt-4.1-mini"

    max_context_chars: int = 24000
    port: int = 8000
    cors_origins: list[str] = field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]
    )
    experience_db_dir: Path = field(
        default_factory=lambda: _BACKEND_ROOT / "data" / "experience"
    )
    agent_adapters: dict[str, AgentAdapterConfig] = field(default_factory=dict)
    config_path: Path = field(default_factory=lambda: _DEFAULT_CONFIG_PATH)

    @property
    def default_model(self) -> str:
        """Backward-compatible default used by single-layer endpoints."""
        return self.model_medium

    def model_for_tier(self, tier: str) -> str:
        if tier == "powerful":
            return self.model_powerful
        return self.model_medium

    def adapter_config(self, agent_id: str) -> AgentAdapterConfig:
        if agent_id in self.agent_adapters:
            return self.agent_adapters[agent_id]
        # Default unknown agents to medium chat models.
        return AgentAdapterConfig(
            agent_id=agent_id,
            tier="medium",
            model=self.model_medium,
            experience_db=None,
        )


def _build_settings(config_path: Path | None = None) -> Settings:
    path = Path(
        os.getenv("LLMHUB_CONFIG_PATH", str(config_path or _DEFAULT_CONFIG_PATH))
    ).expanduser()
    raw = _load_yaml_config(path)
    llmhub = raw.get("llmhub") or {}
    app = raw.get("app") or {}
    models = llmhub.get("models") or {}

    base_url = os.getenv(
        "LLMHUB_BASE_URL",
        str(llmhub.get("base_url") or "https://llmhub.platforms.pfizer/v1"),
    ).rstrip("/")
    if not base_url.endswith("/v1"):
        # Accept host-only config and normalize to OpenAI-compatible root.
        base_url = f"{base_url}/v1"

    api_key = os.getenv("LLMHUB_API_KEY") or str(llmhub.get("api_key") or "")
    user_agent = os.getenv(
        "LLMHUB_USER_AGENT",
        str(llmhub.get("user_agent") or "c4-model-visualizer/1.0"),
    )
    timeout = float(
        os.getenv(
            "LLM_REQUEST_TIMEOUT_SECONDS",
            str(llmhub.get("timeout_seconds") or 120),
        )
    )

    powerful = os.getenv(
        "LLMHUB_MODEL_POWERFUL",
        str(models.get("powerful") or "gpt-4o"),
    )
    medium = os.getenv(
        "LLMHUB_MODEL_MEDIUM",
        str(models.get("medium") or "gpt-4.1-mini"),
    )

    max_context = int(
        os.getenv("MAX_CONTEXT_CHARS", str(app.get("max_context_chars") or 24000))
    )
    port = int(os.getenv("PORT", str(app.get("port") or 8000)))

    if os.getenv("CORS_ORIGINS"):
        cors = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    else:
        cors_raw = app.get("cors_origins") or []
        cors = [str(o) for o in cors_raw] if cors_raw else [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]

    experience_dir = Path(
        os.getenv(
            "EXPERIENCE_DB_DIR",
            str(app.get("experience_db_dir") or (_BACKEND_ROOT / "data" / "experience")),
        )
    )
    if not experience_dir.is_absolute():
        experience_dir = (_BACKEND_ROOT / experience_dir).resolve()

    agents_raw = llmhub.get("agents") or {}
    agent_adapters: dict[str, AgentAdapterConfig] = {}
    for agent_id, cfg in agents_raw.items():
        if not isinstance(cfg, dict):
            continue
        tier = str(cfg.get("tier") or "medium")
        model = powerful if tier == "powerful" else medium
        exp_path = cfg.get("experience_db")
        experience_db: Path | None = None
        if exp_path:
            experience_db = Path(str(exp_path))
            if not experience_db.is_absolute():
                experience_db = (_BACKEND_ROOT / experience_db).resolve()
        agent_adapters[str(agent_id)] = AgentAdapterConfig(
            agent_id=str(agent_id),
            tier=tier,
            model=model,
            experience_db=experience_db,
        )

    # Ensure the four layer specialists always have experience DBs configured.
    for layer_agent, db_name in (
        ("subagent-context", "context.db"),
        ("subagent-container", "container.db"),
        ("subagent-component", "component.db"),
        ("subagent-code", "code.db"),
    ):
        if layer_agent not in agent_adapters:
            agent_adapters[layer_agent] = AgentAdapterConfig(
                agent_id=layer_agent,
                tier="medium",
                model=medium,
                experience_db=experience_dir / db_name,
            )
        elif agent_adapters[layer_agent].experience_db is None:
            current = agent_adapters[layer_agent]
            agent_adapters[layer_agent] = AgentAdapterConfig(
                agent_id=current.agent_id,
                tier=current.tier,
                model=current.model,
                experience_db=experience_dir / db_name,
            )

    return Settings(
        llmhub_base_url=base_url,
        llmhub_api_key=api_key,
        llmhub_user_agent=user_agent,
        request_timeout_seconds=timeout,
        model_powerful=powerful,
        model_medium=medium,
        max_context_chars=max_context,
        port=port,
        cors_origins=cors,
        experience_db_dir=experience_dir,
        agent_adapters=agent_adapters,
        config_path=path,
    )


settings = _build_settings()
