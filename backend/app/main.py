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
from app.config import settings
from app.doc_agent import documentation_agent
from app.llmhub_adapter import (
    filter_chat_models,
    list_models as llmhub_list_models,
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


class CodeAnalysisRequest(BaseModel):
    source: str = Field(
        default="..",
        description="Local repository path to inspect with the 17 adapted Coding & UI/UX Agent Skills.",
    )


@app.get("/")
def root() -> dict:
    return {
        "service": "c4-model-visualizer multi-agent backend",
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
            "/api/docs/generate",
            "/api/docs/reference",
            "/api/docs/reference/preview",
            "/api/c4/cancel",
            "/api/c4/model",
            "/api/c4/{layer}",
            "/api/catalog",
            "/api/catalog/{id}",
            "/api/catalog/{id}/open",
            "/api/catalog/profile",
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


@app.post("/api/docs/generate")
def generate_documentation(request: DocumentationRequest) -> dict:
    try:
        return documentation_agent.generate_documentation_suite(
            project_path=request.project_path,
            output_folder=request.output_folder,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
