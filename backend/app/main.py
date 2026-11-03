"""FastAPI service that generates C4 diagrams, Code & UI/UX Analysis reports,
and Confluence documentation from a source tree using a multi-agent pipeline.

Run with: uvicorn app.main:app --reload --port 8000
See README.md for required setup and scripts/run_doc_agent.py to run the
Documentation Agent (`c4-doc-agent`).
"""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import APIConnectionError
from pydantic import BaseModel, Field

from app.agents import manager_agent
from app.c4_service import generate_layer
from app.cancel_registry import AnalysisCancelled, begin_job, cancel_job, end_job
from app.catalog_store import catalog_store
from app.config import apply_llmhub_credentials, mask_api_key, settings
from app.confluence_publish import (
    ConfluencePublishError,
    publish_documentation_to_confluence,
)
from app.doc_agent import documentation_agent
from app.llmhub_adapter import (
    filter_chat_models,
    get_adapter,
    list_models as llmhub_list_models,
    reset_adapters,
)
from app.schemas import (
    AnalyzeRequest,
    CancelRequest,
    HierarchyModelResponse,
    Layer,
    LayerResponse,
    ModelSourceRequest,
)
from app.skills_registry import (
    list_skill_descriptors,
    skill_execute_sandbox_with_dummy_data,
    skill_run_code_and_ux_analysis,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Orthos — multi-agent C4, code analysis & documentation backend",
    description="Orthos generates C4 model JSON, 17-skill Code & UI/UX Analysis reports, sandbox verification, and Confluence documentation.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DocumentationRequest(BaseModel):
    project_path: str = Field(
        default="..",
        description="Path to the project root to document.",
    )
    output_folder: str = Field(
        default="../documentation",
        description="Output directory where Mermaid, SVG, PNG, and Confluence Markdown files are written.",
    )


class ReferenceDocsRequest(BaseModel):
    source: str = Field(
        description="Local repository path (typically the same source used for C4 analysis).",
    )
    output_folder: str | None = Field(
        default=None,
        description="Optional output directory (defaults to <source>/documentation/reference).",
    )
    style: str = Field(
        default="auto",
        description="Documentation style: auto | sphinx | typedoc | markdown.",
    )
    force: bool = Field(
        default=False,
        description="When true, regenerate even if a matching cache exists.",
    )


class CodeAnalysisRequest(BaseModel):
    source: str = Field(
        default="..",
        description="Local repository path to inspect with the 17 adapted Coding & UI/UX Agent Skills.",
    )


class ExplainComponentRequest(BaseModel):
    id: str = Field(default="", description="Node id")
    name: str = Field(description="Component / node display name")
    kind: str = Field(default="", description="C4 kind")
    layer: str = Field(default="", description="C4 layer id")
    technology: str = Field(default="", description="Technology stack label")
    description: str = Field(default="", description="Existing node description")
    mode: str = Field(
        default="compact",
        description="compact (≤50 words) or deep (full architecture context).",
    )
    model: str | None = Field(
        default=None,
        description="Optional LLMHub model id (must be in the configured/available list).",
    )
    layers_context: dict | None = Field(
        default=None,
        description="Optional C4 layers payload for deep explanations.",
    )


class DocsPublishRequest(BaseModel):
    output_folder: str = Field(
        description="Folder produced by /api/docs/generate (contains CONFLUENCE_*.md and images/png).",
    )
    page_id: str | None = Field(
        default=None,
        description="Confluence page id. Falls back to CONFLUENCE_PAGE_ID / URL parse.",
    )
    page_url: str | None = Field(
        default=None,
        description="Full Confluence page URL (used to derive page id / base URL).",
    )
    prefer: str = Field(
        default="both",
        description="Content mode: both | markdown | png",
    )
    title: str | None = Field(
        default=None,
        description="Optional page title override.",
    )


class DocsPipelineRequest(BaseModel):
    project_path: str = Field(
        description="Repository root to document (CI workspace path).",
    )
    output_folder: str | None = Field(
        default=None,
        description="Docs output folder (defaults to <project_path>/documentation).",
    )
    publish: bool = Field(
        default=False,
        description="When true, publish generated docs to Confluence after generate.",
    )
    page_id: str | None = None
    page_url: str | None = None
    prefer: str = "both"
    title: str | None = None


@app.get("/")
def root() -> dict:
    return {
        "service": "orthos-docs-service",
        "product": "Orthos",
        "mode": "api",
        "llmhub_base_url": settings.llmhub_base_url,
        "models": {
            "powerful": settings.model_powerful,
            "medium": settings.model_medium,
            "options": settings.model_options,
        },
        "config_path": str(settings.config_path),
        "architecture": {
            "manager": {
                "id": manager_agent.agent_id,
                "adapter_tier": manager_agent.adapter.tier,
                "model": manager_agent.adapter.model,
            },
            "supervisor": {
                "id": manager_agent.supervisor.agent_id,
                "adapter_tier": manager_agent.supervisor.adapter.tier,
                "model": manager_agent.supervisor.adapter.model,
            },
            "subagents": [
                {
                    "id": s.agent_id,
                    "adapter_tier": s.adapter.tier,
                    "model": s.adapter.model,
                    "experience_db": str(s.adapter.experience_db)
                    if s.adapter.experience_db
                    else None,
                }
                for s in manager_agent.supervisor.subagents
            ],
            "documentation_agent": documentation_agent.agent_id,
        },
        "endpoints": [
            "/health",
            "/api/agents",
            "/api/skills",
            "/api/analysis/run",
            "/api/sandbox/run",
            "/api/explain/component",
            "/api/docs/generate",
            "/api/docs/publish",
            "/api/docs/pipeline",
            "/api/docs/reference",
            "/api/docs/reference/preview",
            "/api/c4/cancel",
            "/api/c4/model",
            "/api/c4/{layer}",
            "/api/catalog",
            "/api/catalog/{id}",
            "/api/catalog/{id}/open",
            "/api/catalog/profile",
            "/api/llmhub/credentials",
            "/api/llmhub/models",
        ],
    }


@app.get("/api/agents")
def describe_agents() -> dict:
    return {
        "manager": {
            "id": manager_agent.agent_id,
            "role": manager_agent.role,
            "responsibility": "Accepts a local path or GitHub URL, prepares the source inventory, and delegates to the Supervisor.",
            "skills": list(manager_agent.skills),
            "llmhub": {
                "tier": manager_agent.adapter.tier,
                "model": manager_agent.adapter.model,
            },
        },
        "supervisor": {
            "id": manager_agent.supervisor.agent_id,
            "role": manager_agent.supervisor.role,
            "responsibility": "Connects the 4 specialist subagents in top-down order (Context -> Container -> Component -> Code) and guarantees hierarchical parent-child traceability across layers.",
            "skills": list(manager_agent.supervisor.skills),
            "llmhub": {
                "tier": manager_agent.supervisor.adapter.tier,
                "model": manager_agent.supervisor.adapter.model,
            },
        },
        "subagents": [
            {
                "id": sub.agent_id,
                "role": sub.role,
                "layer": sub.layer,
                "skills": list(sub.skills),
                "llmhub": {
                    "tier": sub.adapter.tier,
                    "model": sub.adapter.model,
                    "experience_db": str(sub.adapter.experience_db)
                    if sub.adapter.experience_db
                    else None,
                },
            }
            for sub in manager_agent.supervisor.subagents
        ],
        "documentation_agent": {
            "id": documentation_agent.agent_id,
            "role": documentation_agent.role,
            "responsibility": "Reads project source code, executes sandbox & evaluation metrics, generates concise Confluence-adaptable Mermaid/SVG/PNG diagrams, and self-reviews for logical discrepancies.",
            "skills": documentation_agent.skills,
        },
    }


@app.get("/api/skills")
def list_skills() -> dict:
    skills = list_skill_descriptors()
    return {
        "count": len(skills),
        "skills": skills,
    }


@app.post("/api/analysis/run")
def run_code_and_ux_analysis(request: CodeAnalysisRequest) -> dict:
    try:
        return skill_run_code_and_ux_analysis(request.source)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/sandbox/run")
def run_sandbox_verification() -> dict:
    return skill_execute_sandbox_with_dummy_data()


def _trim_words(text: str, max_words: int = 50) -> str:
    words = (text or "").strip().split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(".,;:") + "…"


def _summarize_layers_context(layers_context: dict | None, focus_name: str) -> str:
    """Compact text digest of C4 layers for deep explain prompts."""
    if not layers_context or not isinstance(layers_context, dict):
        return "No additional layer context provided."
    lines: list[str] = []
    for layer_id in ("context", "container", "component", "code"):
        layer = layers_context.get(layer_id) or {}
        if not isinstance(layer, dict):
            continue
        nodes = layer.get("nodes") or []
        if not isinstance(nodes, list):
            continue
        titles = []
        for node in nodes[:18]:
            if not isinstance(node, dict):
                continue
            data = node.get("data") or {}
            if not isinstance(data, dict):
                continue
            label = str(data.get("name") or node.get("id") or "").strip()
            if not label:
                continue
            kind = str(data.get("kind") or "").strip()
            titles.append(f"{label} ({kind})" if kind else label)
        if titles:
            lines.append(f"{layer_id}: " + "; ".join(titles))
        edges = layer.get("edges") or []
        if isinstance(edges, list) and edges:
            rels = []
            for edge in edges[:12]:
                if not isinstance(edge, dict):
                    continue
                src = str(edge.get("source") or "")
                tgt = str(edge.get("target") or "")
                label = str(edge.get("label") or "").strip()
                if src and tgt:
                    rels.append(f"{src}→{tgt}" + (f" ({label})" if label else ""))
            if rels:
                lines.append(f"{layer_id} relations: " + "; ".join(rels))
    if not lines:
        return "No additional layer context provided."
    lines.append(f"Focus component: {focus_name}")
    return "\n".join(lines)


def _resolve_explain_model(requested: str | None, *, prefer_powerful: bool = False) -> str:
    """Pick a chat model that exists in the configured LLMHub options.

    Avoids hard-failing on defaults like ``gpt-4o`` when the provider does not
    expose that model id.
    """
    options = filter_chat_models(list(settings.model_options))
    allowed = set(options)

    def _ok(candidate: str | None) -> str | None:
        value = (candidate or "").strip()
        if not value:
            return None
        if allowed and value not in allowed:
            return None
        return value

    picked = _ok(requested)
    if picked:
        return picked
    if prefer_powerful:
        picked = _ok(settings.model_powerful)
        if picked:
            return picked
    picked = _ok(settings.model_medium)
    if picked:
        return picked
    if options:
        return options[0]
    return (settings.model_medium or "gpt-4.1-mini").strip()


@app.post("/api/explain/component")
def explain_component(request: ExplainComponentRequest) -> dict:
    """LLMHub explanation of a selected C4 component (compact or deep)."""
    if not settings.llmhub_api_key:
        raise HTTPException(
            status_code=400,
            detail="LLMHub is not configured. Set LLMHUB_API_KEY in Profile settings.",
        )
    name = (request.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Component name is required.")

    mode = (request.mode or "compact").strip().lower()
    if mode not in {"compact", "deep"}:
        raise HTTPException(status_code=400, detail="mode must be compact or deep")

    model = _resolve_explain_model(request.model, prefer_powerful=(mode == "deep"))

    if mode == "deep":
        system = (
            "You are a principal software architect explaining a C4 model component in depth. "
            "Use the full architecture context. Cover: role, responsibilities, collaborators, "
            "data/control flow, and why it exists. "
            "Format with short paragraphs separated by blank lines. "
            "You may use **bold** for component names. No bullet lists unless essential. Avoid fluff."
        )
        context_block = _summarize_layers_context(request.layers_context, name)
        user = (
            f"Deep-explain this C4 component using the architecture context.\n"
            f"Name: {name}\n"
            f"Kind: {request.kind or 'unknown'}\n"
            f"Layer: {request.layer or 'unknown'}\n"
            f"Technology: {request.technology or 'n/a'}\n"
            f"Description: {request.description or 'n/a'}\n\n"
            f"Architecture context:\n{context_block}\n"
        )
        max_words = 320
    else:
        system = (
            "You explain software architecture components for busy engineers. "
            "Reply in plain English only. Maximum 50 words. No bullets, no markdown."
        )
        user = (
            f"Explain this C4 component briefly.\n"
            f"Name: {name}\n"
            f"Kind: {request.kind or 'unknown'}\n"
            f"Layer: {request.layer or 'unknown'}\n"
            f"Technology: {request.technology or 'n/a'}\n"
            f"Description: {request.description or 'n/a'}\n"
        )
        max_words = 50

    try:
        adapter = get_adapter("c4-doc-agent")
        raw = adapter.chat_text(system, user, model=model, temperature=0.2)
        explanation = _trim_words(raw, max_words)
        return {
            "explanation": explanation,
            "model": model,
            "mode": mode,
            "word_count": len(explanation.split()),
            "component": {
                "id": request.id,
                "name": name,
                "kind": request.kind,
                "layer": request.layer,
            },
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/docs/generate")
def generate_documentation(request: DocumentationRequest) -> dict:
    try:
        return documentation_agent.generate_documentation_suite(
            project_path=request.project_path,
            output_folder=request.output_folder,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/docs/publish")
def publish_documentation(request: DocsPublishRequest) -> dict:
    """Upload Orthos doc artifacts to an existing Confluence page (CI / service use)."""
    prefer = (request.prefer or "both").strip().lower()
    if prefer not in {"both", "markdown", "md", "png"}:
        raise HTTPException(
            status_code=400,
            detail="prefer must be one of: both, markdown, png",
        )
    try:
        return publish_documentation_to_confluence(
            request.output_folder,
            page_id=request.page_id,
            page_url=request.page_url,
            prefer="markdown" if prefer == "md" else prefer,
            title_override=request.title,
        )
    except ConfluencePublishError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/docs/pipeline")
def documentation_pipeline(request: DocsPipelineRequest) -> dict:
    """Headless generate (+ optional Confluence publish) for CI on PR merge."""
    project_path = request.project_path.strip()
    if not project_path:
        raise HTTPException(status_code=400, detail="project_path is required")
    output_folder = (request.output_folder or "").strip() or f"{project_path.rstrip('/')}/documentation"

    try:
        generated = documentation_agent.generate_documentation_suite(
            project_path=project_path,
            output_folder=output_folder,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result: dict = {"generate": generated, "publish": None}
    if not request.publish:
        return result

    prefer = (request.prefer or "both").strip().lower()
    if prefer not in {"both", "markdown", "md", "png"}:
        raise HTTPException(
            status_code=400,
            detail="prefer must be one of: both, markdown, png",
        )
    try:
        result["publish"] = publish_documentation_to_confluence(
            output_folder,
            page_id=request.page_id,
            page_url=request.page_url,
            prefer="markdown" if prefer == "md" else prefer,
            title_override=request.title,
        )
    except ConfluencePublishError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


@app.post("/api/docs/reference/preview")
def preview_code_reference_docs(request: ReferenceDocsRequest) -> dict:
    """Browse code-layer symbols and the recommended Sphinx/TypeDoc/Markdown style (no write)."""
    from app.reference_docs import preview_reference_docs

    style = (request.style or "auto").strip().lower()
    if style not in {"auto", "sphinx", "typedoc", "markdown"}:
        raise HTTPException(
            status_code=400,
            detail="style must be one of: auto, sphinx, typedoc, markdown",
        )
    try:
        return preview_reference_docs(
            project_path=request.source,
            style=style,  # type: ignore[arg-type]
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/docs/reference")
def generate_code_reference_docs(request: ReferenceDocsRequest) -> dict:
    """Build Sphinx / TypeDoc / Markdown reference docs from the code layer inventory."""
    from app.reference_docs import generate_reference_docs

    style = (request.style or "auto").strip().lower()
    if style not in {"auto", "sphinx", "typedoc", "markdown"}:
        raise HTTPException(
            status_code=400,
            detail="style must be one of: auto, sphinx, typedoc, markdown",
        )
    try:
        return generate_reference_docs(
            project_path=request.source,
            output_folder=request.output_folder,
            style=style,  # type: ignore[arg-type]
            force=bool(request.force),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/c4/model", response_model=HierarchyModelResponse)
def generate_c4_hierarchy_model(request: ModelSourceRequest) -> HierarchyModelResponse:
    job_id = (request.job_id or "").strip() or None
    if job_id:
        begin_job(job_id)
    try:
        result = manager_agent.analyze(
            source=request.source,
            source_type=request.source_type,
            use_llm=request.use_llm,
            model=request.model,
            job_id=job_id,
        )
        # Persist metadata + full diagram payload so Catalog can reopen without re-analysis.
        try:
            catalog_store.upsert_analysis(result.model_dump(mode="json"))
        except Exception:  # noqa: BLE001
            logging.getLogger(__name__).exception("Failed to persist catalog entry")
        return result
    except AnalysisCancelled as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        end_job(job_id)


class ProfileUpdateRequest(BaseModel):
    display_name: str = Field(default="Architect", max_length=48)


class LlmHubCredentialsUpdate(BaseModel):
    api_key: str | None = Field(
        default=None,
        description="New LLMHub API key. Omit or null to keep the existing key.",
    )
    base_url: str | None = Field(
        default=None,
        description="LLMHub base URL (OpenAI-compatible /v1). Omit to keep current.",
    )


@app.get("/api/llmhub/credentials")
def get_llmhub_credentials() -> dict:
    """Return LLMHub connection settings with a masked API key (never the raw secret)."""
    return {
        "base_url": settings.llmhub_base_url,
        "api_key_configured": bool(settings.llmhub_api_key),
        "api_key_masked": mask_api_key(settings.llmhub_api_key),
        "display_name": catalog_store.get_profile_name(),
    }


@app.put("/api/llmhub/credentials")
def update_llmhub_credentials(request: LlmHubCredentialsUpdate) -> dict:
    """Update LLMHub credentials at runtime and persist them to backend/.env."""
    incoming_key = request.api_key
    # Ignore accidental re-submit of the masked display value.
    if incoming_key is not None:
        masked = mask_api_key(settings.llmhub_api_key)
        if incoming_key.strip() == "" and not settings.llmhub_api_key:
            incoming_key = ""
        elif (
            incoming_key == masked
            or (masked and incoming_key.startswith(masked[:4]) and "•" in incoming_key)
        ):
            incoming_key = None

    try:
        result = apply_llmhub_credentials(
            api_key=incoming_key,
            base_url=request.base_url,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    reset_adapters()
    result["display_name"] = catalog_store.get_profile_name()
    return result


@app.get("/api/catalog")
def list_catalog(q: str | None = None) -> dict:
    """List previously analyzed repositories (metadata only)."""
    entries = catalog_store.list_entries(query=q)
    return {
        "entries": [e.as_dict() for e in entries],
        "count": len(entries),
        "profile": {"display_name": catalog_store.get_profile_name()},
    }


@app.get("/api/catalog/profile")
def get_catalog_profile() -> dict:
    return {"display_name": catalog_store.get_profile_name()}


@app.put("/api/catalog/profile")
def update_catalog_profile(request: ProfileUpdateRequest) -> dict:
    name = catalog_store.set_profile_name(request.display_name)
    return {"display_name": name}


@app.get("/api/catalog/{entry_id}")
def get_catalog_entry(entry_id: str) -> dict:
    entry = catalog_store.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog entry not found.")
    return entry.as_dict()


@app.post("/api/catalog/{entry_id}/open")
def open_catalog_entry(entry_id: str) -> dict:
    """Touch last_opened_at and return the cached HierarchyModelResponse payload."""
    opened = catalog_store.open_entry(entry_id)
    if not opened:
        raise HTTPException(status_code=404, detail="Catalog entry not found.")
    entry, payload = opened
    return {"entry": entry.as_dict(), "model": payload}


@app.delete("/api/catalog/{entry_id}")
def delete_catalog_entry(entry_id: str) -> dict:
    deleted = catalog_store.delete_entry(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Catalog entry not found.")
    return {"deleted": True, "id": entry_id}


@app.delete("/api/catalog")
def clear_catalog() -> dict:
    removed = catalog_store.clear()
    return {"deleted": removed}


@app.post("/api/c4/cancel")
def cancel_c4_analysis(request: CancelRequest) -> dict:
    """Signal an in-flight analysis job to stop at the next safe checkpoint."""
    job_id = request.job_id.strip()
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id is required.")
    found = cancel_job(job_id)
    return {
        "job_id": job_id,
        "cancelled": found,
        "detail": (
            "Stop signal sent; analysis will halt at the next layer checkpoint."
            if found
            else "No running job found for that id (it may have already finished)."
        ),
    }


@app.get("/health")
def health() -> dict:
    if not settings.llmhub_api_key:
        return {
            "status": "llmhub_unconfigured",
            "llmhub_base_url": settings.llmhub_base_url,
            "hint": "Set LLMHUB_API_KEY in .env or config/llmhub.yaml. See scripts/check_llmhub.py.",
        }
    try:
        models = filter_chat_models(llmhub_list_models())
    except APIConnectionError:
        return {
            "status": "llmhub_unreachable",
            "llmhub_base_url": settings.llmhub_base_url,
            "hint": "Confirm Pfizer network/VPN access to https://llmhub.platforms.pfizer",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "llmhub_error",
            "llmhub_base_url": settings.llmhub_base_url,
            "error": str(exc),
        }
    return {
        "status": "ok",
        "llmhub_base_url": settings.llmhub_base_url,
        "models": {
            "powerful": settings.model_powerful,
            "medium": settings.model_medium,
            "options": settings.model_options,
        },
        "models_loaded": models,
    }


@app.get("/api/llmhub/models")
def llmhub_model_catalog() -> dict:
    """Return configured .env/yaml chat-model options plus live LLMHub catalog when reachable.

    Embedding / image / audio model IDs are filtered out of the UI dropdown.
    """
    live: list[str] = []
    live_status = "skipped"
    live_error: str | None = None
    if settings.llmhub_api_key:
        try:
            live = filter_chat_models(llmhub_list_models())
            live_status = "ok"
        except APIConnectionError as exc:
            live_status = "unreachable"
            live_error = str(exc)
        except Exception as exc:  # noqa: BLE001
            live_status = "error"
            live_error = str(exc)

    # Prefer configured chat options for the dropdown; append any live chat models.
    options = filter_chat_models(list(settings.model_options))
    for mid in live:
        if mid not in options:
            options.append(mid)

    return {
        "base_url": settings.llmhub_base_url,
        "default_powerful": settings.model_powerful,
        "default_medium": settings.model_medium,
        "options": options,
        "configured_options": filter_chat_models(list(settings.model_options)),
        "live_status": live_status,
        "live_models": live,
        "live_error": live_error,
    }


@app.post("/api/c4/{layer}", response_model=LayerResponse)
def generate_c4_layer(layer: Layer, request: AnalyzeRequest) -> LayerResponse:
    try:
        return generate_layer(request.repo_path, layer, model=request.model)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except APIConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Could not reach Pfizer LLMHub at {settings.llmhub_base_url}. "
                "Check VPN / credentials (scripts/check_llmhub.py)."
            ),
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Model did not return valid JSON after retry: {exc}",
        ) from exc
