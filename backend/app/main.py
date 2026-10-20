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

from app import llm_client
from app.agents import manager_agent
from app.c4_service import generate_layer
from app.config import settings
from app.doc_agent import documentation_agent
from app.schemas import (
    AnalyzeRequest,
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
    title="C4 Model Visualiser — multi-agent, code analysis & documentation backend",
    description="Generates C4 model JSON, 17-skill Code & UI/UX Analysis reports, sandbox verification, and Confluence documentation.",
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


class CodeAnalysisRequest(BaseModel):
    source: str = Field(
        default="..",
        description="Local repository path to inspect with the 17 adapted Coding & UI/UX Agent Skills.",
    )


@app.get("/")
def root() -> dict:
    return {
        "service": "c4-model-visualizer multi-agent backend",
        "lm_studio_base_url": settings.lm_studio_base_url,
        "default_model": settings.lm_studio_model,
        "architecture": {
            "manager": manager_agent.agent_id,
            "supervisor": manager_agent.supervisor.agent_id,
            "subagents": [s.agent_id for s in manager_agent.supervisor.subagents],
            "documentation_agent": documentation_agent.agent_id,
        },
        "endpoints": [
            "/health",
            "/api/agents",
            "/api/skills",
            "/api/analysis/run",
            "/api/sandbox/run",
            "/api/docs/generate",
            "/api/c4/model",
            "/api/c4/{layer}",
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
        },
        "supervisor": {
            "id": manager_agent.supervisor.agent_id,
            "role": manager_agent.supervisor.role,
            "responsibility": "Connects the 4 specialist subagents in top-down order (Context -> Container -> Component -> Code) and guarantees hierarchical parent-child traceability across layers.",
            "skills": list(manager_agent.supervisor.skills),
        },
        "subagents": [
            {
                "id": sub.agent_id,
                "role": sub.role,
                "layer": sub.layer,
                "skills": list(sub.skills),
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


@app.post("/api/c4/model", response_model=HierarchyModelResponse)
def generate_c4_hierarchy_model(request: ModelSourceRequest) -> HierarchyModelResponse:
    try:
        return manager_agent.analyze(
            source=request.source,
            source_type=request.source_type,
            use_llm=request.use_llm,
            model=request.model,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    try:
        models = llm_client.list_models()
    except APIConnectionError:
        return {
            "status": "lm_studio_unreachable",
            "lm_studio_base_url": settings.lm_studio_base_url,
            "hint": "Start LM Studio's local server: `lms server start`, or Developer tab -> Start Server.",
        }
    return {"status": "ok", "lm_studio_base_url": settings.lm_studio_base_url, "models_loaded": models}


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
            detail=f"Could not reach LM Studio at {settings.lm_studio_base_url}. Is the local server running?",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Model did not return valid JSON after retry: {exc}",
        ) from exc
