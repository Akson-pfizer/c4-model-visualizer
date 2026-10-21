#!/usr/bin/env python3
"""Verifies Pfizer LLMHub connectivity for the C4 multi-agent backend.

Checks:
1. ``config/llmhub.yaml`` (or env) provides a non-empty API key.
2. ``GET /v1/models`` succeeds.
3. A chat completion against the configured medium model returns JSON.

Docs: https://docs.platforms.pfizer/llmhub/docs/llmhub-endpoints
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import APIConnectionError, APIStatusError  # noqa: E402

from app.config import settings  # noqa: E402
from app.llmhub_adapter import get_adapter  # noqa: E402


def main() -> int:
    print(f"Config file : {settings.config_path}")
    print(f"LLMHub URL  : {settings.llmhub_base_url}")
    print(f"User-Agent  : {settings.llmhub_user_agent}")
    print(f"Powerful    : {settings.model_powerful}  (Manager / Supervisor)")
    print(f"Medium      : {settings.model_medium}  (layer specialists)")
    print(f"API key set : {'yes' if bool(settings.llmhub_api_key) else 'NO'}")

    if not settings.llmhub_api_key:
        print(
            "\n[FAIL] LLMHUB_API_KEY is empty.\n"
            "  -> Set it in config/llmhub.yaml (`api_key: ${LLMHUB_API_KEY}`) "
            "or export LLMHUB_API_KEY in .env."
        )
        return 1

    manager = get_adapter("c4-manager")
    try:
        models = manager.list_models()
    except APIConnectionError:
        print(
            "\n[FAIL] Could not reach LLMHub.\n"
            "  -> Confirm VPN / Pfizer network access to "
            "https://llmhub.platforms.pfizer"
        )
        return 1
    except APIStatusError as exc:
        print(f"\n[FAIL] LLMHub returned HTTP {exc.status_code}: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\n[FAIL] Unexpected error listing models: {exc}")
        return 1

    print(f"[OK] Server reachable. Models available: {len(models)}")
    if models:
        preview = ", ".join(models[:8])
        print(f"     sample: {preview}{'…' if len(models) > 8 else ''}")

    for label, agent_id, model in (
        ("powerful", "c4-manager", settings.model_powerful),
        ("medium", "subagent-context", settings.model_medium),
    ):
        if models and model not in models:
            print(
                f"[WARN] {label} model '{model}' is not in /v1/models for this key. "
                f"Update config/llmhub.yaml models.{label}."
            )
        adapter = get_adapter(agent_id)
        print(f"\nSending test chat_json via {agent_id} ({label}/{model})...")
        try:
            result = adapter.chat_json(
                system_prompt="Respond with strict JSON only.",
                user_prompt='Return exactly this JSON object: {"ok": true}',
                model=model,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] Chat completion failed for {agent_id}: {exc}")
            return 1
        print(f"[OK] {agent_id} responded: {result}")

    print(
        "\nSetup looks good — start the API with:\n"
        "  uvicorn app.main:app --reload --port 8000"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
