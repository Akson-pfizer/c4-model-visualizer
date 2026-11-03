"""Pydantic models mirroring the frontend's C4 layer JSON contract exactly.

The frontend (c4-model-visualizer/frontend) currently reads this exact shape
from static files in src/lib/data/*.json. These models are the schema a real
backend endpoint should return, documented in that project's
claude_output/frontend_implementation.md. Keep this file in sync with that
contract if either side changes.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal[
    "person",
    "system",
    "systemExternal",
    "container",
    "containerDb",
    "containerExternal",
    "component",
    "codeInterface",
    "codeClass",
    "codeEnum",
]

Layer = Literal["context", "container", "component", "code"]

# Which element kinds are valid at each C4 layer — used both to steer the LLM
# prompt and to validate its output.
KINDS_BY_LAYER: dict[Layer, tuple[Kind, ...]] = {
    "context": ("person", "system", "systemExternal"),
    "container": ("person", "container", "containerDb", "containerExternal", "systemExternal"),
    "component": ("container", "containerDb", "component", "systemExternal"),
    "code": ("codeInterface", "codeClass", "codeEnum"),
}


class Position(BaseModel):
    x: float
    y: float


class Size(BaseModel):
    width: float
    height: float


class LegendItem(BaseModel):
    kind: Kind
    label: str


class Boundary(BaseModel):
    id: str
    label: str
    subtitle: str | None = Field(
        default=None,
        description="Upper-layer stereotype & technology badge, e.g. 'Upper Layer: Container · Zoomed In · Next.js 16 / React 19'.",
    )
    description: str | None = Field(
        default=None,
        description="Business or architectural summary carried forward from the upper-layer node to explain the zoomed-in scope.",
    )
    upperLayer: Layer | None = Field(
        default=None,
        description="The upper C4 layer ('context', 'container', 'component') from which this transparent boundary was carried forward.",
    )
    sourceNodeId: str | None = Field(
        default=None,
        description="The node ID in the upper layer that was zoomed in / opened up to form this transparent boundary.",
    )
    position: Position
    size: Size


class NodeData(BaseModel):
    kind: Kind
    name: str
    technology: str | None = None
    description: str
    parentNodeId: str | None = Field(
        default=None,
        description="ID of the node in the parent C4 layer (Context -> Container -> Component -> Code) that this element belongs to.",
    )
    sourceScope: str | None = Field(
        default=None,
        description="Directory or module scope path governed by this node, used to carry upper-layer context down into child layers.",
    )


class C4Node(BaseModel):
    id: str
    type: Literal["c4Node"] = "c4Node"
    position: Position
    parentId: str | None = None
    extent: Literal["parent"] | None = None
    data: NodeData


class EdgeData(BaseModel):
    technology: str | None = None


class C4Edge(BaseModel):
    id: str
    source: str
    target: str
    type: Literal["c4Edge"] = "c4Edge"
    label: str
    data: EdgeData = Field(default_factory=EdgeData)


class LayerResponse(BaseModel):
    layer: Layer
    title: str
    subtitle: str
    description: str
    note: str | None = None
    legend: list[LegendItem]
    boundaries: list[Boundary] = Field(default_factory=list)
    nodes: list[C4Node]
    edges: list[C4Edge]


class LLMExtraction(BaseModel):
    """What we actually ask the model to produce.

    Narrower than LayerResponse: title/subtitle/description/note/legend are
    filled in deterministically by the service layer (see c4_service.py), not
    left to the model to invent — that keeps layer framing and the fixed C4
    guidance notes consistent regardless of which local model is loaded.
    """

    boundaries: list[Boundary] = Field(default_factory=list)
    nodes: list[C4Node]
    edges: list[C4Edge]


class AnalyzeRequest(BaseModel):
    repo_path: str = Field(
        description="Absolute or relative path to the source tree to analyze, or a GitHub URL."
    )
    model: str | None = Field(
        default=None,
        description="Override the LLMHub chat model id (defaults to medium tier in config/llmhub.yaml).",
    )


class ModelSourceRequest(BaseModel):
    source: str = Field(
        description="Local filesystem path or GitHub URL (e.g. https://github.com/org/repo) to analyze."
    )
    source_type: Literal["local", "github"] | None = Field(
        default=None,
        description="Expected source type selected in the UI ('local' or 'github').",
    )
    use_llm: bool = Field(
        default=False,
        description="Whether to use Pfizer LLMHub when reachable (falls back to deterministic AST/source analysis automatically).",
    )
    model: str | None = Field(
        default=None,
        description="Optional LLMHub model override when use_llm is enabled (specialists default to medium tier).",
    )
    job_id: str | None = Field(
        default=None,
        description="Client-generated id so the UI can stop this run via POST /api/c4/cancel.",
    )


class CancelRequest(BaseModel):
    job_id: str = Field(description="The job_id previously sent with POST /api/c4/model.")


class AgentReport(BaseModel):
    agent_id: str
    role: str
    layer: Layer | None = None
    status: Literal["completed", "fallback"] = "completed"
    summary: str
    produced_nodes: int = 0
    produced_edges: int = 0


class HierarchyTreeNode(BaseModel):
    id: str
    name: str
    layer: Layer
    kind: Kind
    technology: str | None = None
    description: str
    parentNodeId: str | None = None
    children: list[HierarchyTreeNode] = Field(default_factory=list)


FolderRole = Literal["container", "component", "shared", "ignore"]
ProjectStyle = Literal["feature_modules", "service_monorepo", "single_app", "mixed"]


class FolderClassificationModel(BaseModel):
    """API view of one classified folder (and optional child folders)."""

    path: str
    name: str
    depth: int = 0
    role: FolderRole
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    file_count: int = 0
    code_file_count: int = 0
    extensions: list[str] = Field(default_factory=list)
    children: list[FolderClassificationModel] = Field(default_factory=list)
    refined_by_llm: bool = False


class ProjectPlanModel(BaseModel):
    """Manager-produced folder role plan for the analyzed repository."""

    root: str
    repo_name: str
    style: ProjectStyle
    summary: str
    folders: list[FolderClassificationModel] = Field(default_factory=list)
    container_scopes: list[str] = Field(default_factory=list)
    component_scopes: list[str] = Field(default_factory=list)
    shared_scopes: list[str] = Field(default_factory=list)


class HierarchyModelResponse(BaseModel):
    source: str
    source_type: Literal["local", "github"]
    repo_name: str
    agents: list[AgentReport]
    layers: dict[Layer, LayerResponse]
    hierarchy: list[HierarchyTreeNode]
    project_plan: ProjectPlanModel | None = Field(
        default=None,
        description="Folder/subfolder role classification (container/component/shared/ignore).",
    )

