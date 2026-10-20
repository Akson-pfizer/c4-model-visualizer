#!/usr/bin/env python3
"""Verifies the required LM Studio setup is actually working:
1. The local server is reachable.
2. The configured model (LM_STUDIO_MODEL) is loaded and can respond.

Run this before starting the FastAPI app — it's the fastest way to tell
"is my local setup correct" from "is there a bug in the app".
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import APIConnectionError  # noqa: E402

from app import llm_client  # noqa: E402
from app.config import settings  # noqa: E402


def main() -> int:
    print(f"LM Studio base URL: {settings.lm_studio_base_url}")

    try:
        models = llm_client.list_models()
    except APIConnectionError:
        print(
            "\n[FAIL] Could not reach LM Studio.\n"
            "  -> Start the server: `lms server start` (CLI) or Developer tab -> Start Server (app)."
        )
        return 1

    print(f"[OK] Server reachable. Loaded models: {models or '(none loaded)'}")

    if not models:
        print(
            "\n[FAIL] No model is loaded.\n"
            "  -> In LM Studio, load a model (e.g. the one in LM_STUDIO_MODEL), "
            "or run `lms load <model-id>`."
        )
        return 1

    target = settings.lm_studio_model
    if target not in models:
        print(
            f"\n[WARN] LM_STUDIO_MODEL='{target}' is not among the loaded models.\n"
            f"  -> Either load it, or set LM_STUDIO_MODEL to one of: {models}"
        )

    print(f"\nSending a test chat completion to '{target}'...")
    try:
        result = llm_client.chat_json(
            system_prompt="Respond with strict JSON only.",
            user_prompt='Return exactly this JSON object: {"ok": true}',
            model=target,
        )
    except Exception as exc:  # noqa: BLE001 — this is a diagnostic script
        print(f"\n[FAIL] Chat completion failed: {exc}")
        return 1

    print(f"[OK] Model responded with parsed JSON: {result}")
    print("\nSetup looks good — you can start the API with:\n  uvicorn app.main:app --reload --port 8000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
