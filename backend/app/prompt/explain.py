"""Explain-chat prompts for C4 component explanations."""

from __future__ import annotations

EXPLAIN_DEEP_SYSTEM = (
    "You are a principal software architect explaining a C4 model component in depth. "
    "Use the full architecture context. Cover: role, responsibilities, collaborators, "
    "data/control flow, and why it exists. "
    "Format with short paragraphs separated by blank lines. "
    "You may use **bold** for component names. No bullet lists unless essential. Avoid fluff."
)

EXPLAIN_COMPACT_SYSTEM = (
    "You explain software architecture components for busy engineers. "
    "Reply in plain English only. Maximum 50 words. No bullets, no markdown."
)


def build_explain_user_prompt(
    *,
    mode: str,
    name: str,
    kind: str,
    layer: str,
    technology: str,
    description: str,
    architecture_context: str = "",
) -> str:
    if mode == "deep":
        return (
            f"Deep-explain this C4 component using the architecture context.\n"
            f"Name: {name}\n"
            f"Kind: {kind or 'unknown'}\n"
            f"Layer: {layer or 'unknown'}\n"
            f"Technology: {technology or 'n/a'}\n"
            f"Description: {description or 'n/a'}\n\n"
            f"Architecture context:\n{architecture_context or 'No additional layer context provided.'}\n"
        )
    return (
        f"Explain this C4 component briefly.\n"
        f"Name: {name}\n"
        f"Kind: {kind or 'unknown'}\n"
        f"Layer: {layer or 'unknown'}\n"
        f"Technology: {technology or 'n/a'}\n"
        f"Description: {description or 'n/a'}\n"
    )
