#!/usr/bin/env python3
"""Deprecated — LM Studio has been replaced by Pfizer LLMHub.

Use ``scripts/check_llmhub.py`` instead.
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "LM Studio support was removed.\n"
        "Use Pfizer LLMHub instead:\n"
        "  python scripts/check_llmhub.py\n"
        "Config: config/llmhub.yaml  ·  Env: LLMHUB_API_KEY\n"
        "Docs: https://docs.platforms.pfizer/llmhub/docs/llmhub-endpoints"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
