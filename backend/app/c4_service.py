"""Orchestrates one layer's extraction: scan -> prompt -> LLM -> validate.

Title/description/note/legend are filled in here deterministically rather than
left to the model — that way layer framing and the fixed C4 guidance notes
stay consistent and exactly match the frontend's static demo data regardless
of which local model is loaded or how well it follows instructions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.llm_client import chat_json
from app.prompts import build_prompt, build_repair_prompt
from app.repo_scanner import build_repo_context
from app.schemas import Kind, Layer, LayerResponse, LegendItem, LLMExtraction

logger = logging.getLogger(__name__)

KIND_LABELS: dict[Kind, str] = {
    "person": "Person",
    "system": "Software System (in scope)",
    "systemExternal": "Software System (external)",
    "container": "Container",
    "containerDb": "Container (database)",
    "containerExternal": "Container (external)",
    "component": "Component",
    "codeInterface": "Interface",
    "codeClass": "Class",
    "codeEnum": "Enum",
}

LAYER_TITLES: dict[Layer, str] = {
    "context": "Context",
    "container": "Container",
    "component": "Component",
    "code": "Code",
}

LAYER_DESCRIPTIONS: dict[Layer, str] = {
    "context": "Business Reference Context: high-level business capabilities, domain workflows, and personas worked on top of the underlying containers and components.",
    "container": "Zoomed-In Business Context: upper-layer business contexts open up with transparent borders to reveal all application, library, hook, and data containers inside.",
    "component": "Zoomed-In Containers: every upper-layer container is carried forward with an enlarged transparent border, opening up to explain all internal components inside it.",
    "code": "Zoomed-In Components: upper-layer components are carried forward with enlarged transparent borders, opening up to show their classes, interfaces, hooks, and functions.",
}

LAYER_NOTES: dict[Layer, str | None] = {
    "context": "Business Reference Layer: maps high-level business capabilities and user roles directly to the containers and components that deliver them.",
    "container": "Upper-layer Business Context nodes are carried forward as transparent dashed boundaries so you can see which business domain each container serves.",
    "component": "All upper-layer Containers (e.g., app, components, lib, hooks, database) are carried forward with enlarged transparent borders so no container disappears when zooming in.",
    "code": "Upper-layer Components are carried forward as enlarged transparent boundaries enclosing their concrete code classes, interfaces, and exported symbols.",
}

MAX_REPAIR_ATTEMPTS = 1


def _build_legend(extraction: LLMExtraction) -> list[LegendItem]:
    seen_kinds: list[Kind] = []
    for node in extraction.nodes:
        if node.data.kind not in seen_kinds:
            seen_kinds.append(node.data.kind)
    return [LegendItem(kind=kind, label=KIND_LABELS[kind]) for kind in seen_kinds]


def _validate_edges(extraction: LLMExtraction) -> None:
    node_ids = {n.id for n in extraction.nodes}
    dangling = [e.id for e in extraction.edges if e.source not in node_ids or e.target not in node_ids]
    if dangling:
        raise ValueError(f"Edges reference unknown node ids: {dangling}")


def _extract_with_retry(layer: Layer, repo_context: str, model: str | None) -> LLMExtraction:
    system_prompt, user_prompt = build_prompt(layer, repo_context)
    raw = chat_json(system_prompt, user_prompt, model=model)

    for attempt in range(1 + MAX_REPAIR_ATTEMPTS):
        try:
            extraction = LLMExtraction.model_validate(raw)
            _validate_edges(extraction)
            return extraction
        except (ValidationError, ValueError) as exc:
            if attempt >= MAX_REPAIR_ATTEMPTS:
                raise
            logger.warning("Validation failed (attempt %d), asking model to repair: %s", attempt + 1, exc)
            repair_prompt = build_repair_prompt(json.dumps(raw), str(exc))
            raw = chat_json(system_prompt, repair_prompt, model=model)

    raise AssertionError("unreachable")


def generate_layer(repo_path: str, layer: Layer, model: str | None = None) -> LayerResponse:
    repo_context = build_repo_context(repo_path)
    extraction = _extract_with_retry(layer, repo_context, model)

    return LayerResponse(
        layer=layer,
        title=LAYER_TITLES[layer],
        subtitle=f"Generated from {Path(repo_path).expanduser().resolve().name}",
        description=LAYER_DESCRIPTIONS[layer],
        note=LAYER_NOTES[layer],
        legend=_build_legend(extraction),
        boundaries=extraction.boundaries,
        nodes=extraction.nodes,
        edges=extraction.edges,
    )
