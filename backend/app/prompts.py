"""Backward-compatible shim — prefer ``from app.prompt import …``."""

from app.prompt.c4 import (  # noqa: F401
    LAYER_FRAMING,
    SYSTEM_PROMPT,
    build_prompt,
    build_repair_prompt,
)
