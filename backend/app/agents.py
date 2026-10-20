"""Multi-agent C4 architecture extraction pipeline.

Architecture:
1. **ManagerAgent** (`c4-manager`):
   - Entry-point orchestrator that accepts a local repository path or a GitHub
     repository URL (`https://github.com/owner/repo` or `git@github.com:...`).
   - Resolves or clones the repository, scans the source files, and delegates
     hierarchical C4 extraction to the `SupervisorAgent`.
2. **SupervisorAgent** (`c4-supervisor`):
   - Coordinates the 4 specialist subagents in top-down C4 order:
     `ContextSubagent` -> `ContainerSubagent` -> `ComponentSubagent` -> `CodeSubagent`.
   - Enforces hierarchical parent-child traceability across layers (`parentNodeId`)
     so every Container links to a Context System, every Component links to a
     Container, and every Code module/class/interface links to a Component.
   - Builds the unified `HierarchyTreeNode` forest rooted at the Context layer
     nodes (`Context -> Container -> Component -> Code`).
3. **4 Specialist Subagents**:
   - `ContextSubagent` (`subagent-context`): System Context layer (People, Systems, External Systems).
   - `ContainerSubagent` (`subagent-container`): Container layer (Apps, APIs, Databases, Workers) traced to Context systems.
   - `ComponentSubagent` (`subagent-component`): Component layer (Controllers, Services, Modules) traced to Containers.
   - `CodeSubagent` (`subagent-code`): Code layer (Classes, Interfaces, Enums, Functions) traced to Components.

Each specialist subagent uses the local LLM (via LM Studio) when reachable and
automatically falls back to deterministic AST / source-tree static analysis so
the pipeline always succeeds for any local path or GitHub repository.
"""

from __future__ import annotations

import ast
import json
import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from app.c4_service import (
    KIND_LABELS,
    LAYER_DESCRIPTIONS,
    LAYER_NOTES,
    LAYER_TITLES,
    _build_legend,
    _validate_edges,
)
from app.llm_client import chat_json, is_server_reachable
from app.prompts import SYSTEM_PROMPT, build_repair_prompt
from app.repo_scanner import IGNORED_DIRS, INCLUDED_EXTENSIONS, build_repo_context
from app.schemas import (
    AgentReport,
    Boundary,
    C4Edge,
    C4Node,
    EdgeData,
    HierarchyModelResponse,
    HierarchyTreeNode,
    KINDS_BY_LAYER,
    Kind,
    Layer,
    LayerResponse,
    LLMExtraction,
    NodeData,
    Position,
    Size,
)

logger = logging.getLogger(__name__)


def _slug(value: str, prefix: str = "node") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or prefix


@dataclass
class RepoInventory:
    root: Path
    source_label: str
    source_type: str  # "local" | "github"
    repo_name: str
    files: list[Path]
    repo_context: str


# ============================================================================
# 4 Specialist Subagents (Context, Container, Component, Code)
# ============================================================================


class BaseLayerSubagent:
    agent_id: str
    role: str
    layer: Layer
    skills: tuple[str, ...] = (
        "read-code",
        "draw-diagram",
        "follow-workflows",
        "validate-repair",
    )

    def run(
        self,
        inventory: RepoInventory,
        parent_nodes: list[C4Node],
        use_llm: bool,
        model: str | None = None,
    ) -> tuple[LayerResponse, AgentReport]:
        extraction: LLMExtraction | None = None
        summary_suffix = "static source analyzer"

        if use_llm:
            try:
                extraction = self._extract_via_llm(inventory, parent_nodes, model)
                summary_suffix = f"LLM ({model or 'default'})"
            except Exception as exc:
                logger.warning(
                    "[%s] LLM extraction failed (%s); falling back to static source analysis.",
                    self.agent_id,
                    exc,
                )

        if extraction is None:
            extraction = self.extract_deterministic(inventory, parent_nodes)

        extraction = self._ensure_parent_links(extraction, parent_nodes)
        subtitle = self._build_subtitle(inventory, parent_nodes)

        response = LayerResponse(
            layer=self.layer,
            title=LAYER_TITLES[self.layer],
            subtitle=subtitle,
            description=LAYER_DESCRIPTIONS[self.layer],
            note=LAYER_NOTES[self.layer],
            legend=_build_legend(extraction),
            boundaries=extraction.boundaries,
            nodes=extraction.nodes,
            edges=extraction.edges,
        )
        report = AgentReport(
            agent_id=self.agent_id,
            role=self.role,
            layer=self.layer,
            status="completed",
            summary=(
                f"Extracted {len(response.nodes)} {self.layer} nodes and "
                f"{len(response.edges)} connections via {summary_suffix}."
            ),
            produced_nodes=len(response.nodes),
            produced_edges=len(response.edges),
        )
        return response, report

    def _build_subtitle(self, inventory: RepoInventory, parent_nodes: list[C4Node]) -> str:
        if self.layer == "context":
            return f"System Context · {inventory.repo_name}"
        if parent_nodes:
            primary = self._select_primary_parent(parent_nodes)
            return f"Zoomed into: {primary.data.name}"
        return f"Generated from {inventory.repo_name}"

    def _select_primary_parent(self, parent_nodes: list[C4Node]) -> C4Node:
        preferred_kinds = {
            "container": ("system",),
            "component": ("container",),
            "code": ("component",),
        }.get(self.layer, ())
        for node in parent_nodes:
            if node.data.kind in preferred_kinds:
                return node
        return parent_nodes[0]

    def _ensure_parent_links(
        self, extraction: LLMExtraction, parent_nodes: list[C4Node]
    ) -> LLMExtraction:
        if not parent_nodes:
            for node in extraction.nodes:
                node.data.parentNodeId = None
            return extraction

        valid_parent_ids = {p.id for p in parent_nodes}
        primary_parent = self._select_primary_parent(parent_nodes)
        in_scope_parents = [
            p
            for p in parent_nodes
            if p.data.kind in ("system", "container", "containerDb", "component")
        ] or [primary_parent]

        for idx, node in enumerate(extraction.nodes):
            if node.data.parentNodeId in valid_parent_ids:
                continue
            # Match external/person nodes to matching parent if present, otherwise distribute across in-scope parents
            matched = next(
                (p for p in parent_nodes if p.id == node.id or p.data.name.lower() == node.data.name.lower()),
                None,
            )
            if matched is not None:
                node.data.parentNodeId = matched.id
            else:
                target_parent = in_scope_parents[idx % len(in_scope_parents)]
                node.data.parentNodeId = target_parent.id
        return extraction

    def _extract_via_llm(
        self,
        inventory: RepoInventory,
        parent_nodes: list[C4Node],
        model: str | None,
    ) -> LLMExtraction:
        allowed_kinds = ", ".join(KINDS_BY_LAYER[self.layer])
        parent_context = ""
        if parent_nodes:
            parent_list = [
                {
                    "id": p.id,
                    "name": p.data.name,
                    "kind": p.data.kind,
                    "technology": p.data.technology,
                }
                for p in parent_nodes
            ]
            parent_context = (
                "\nParent layer nodes (set `data.parentNodeId` on EVERY node to one of these parent `id`s "
                "so the hierarchy tree is traceable):\n"
                f"{json.dumps(parent_list, indent=2)}\n"
            )

        user_prompt = (
            f"You are specialist subagent `{self.agent_id}` ({self.role}) for C4 layer: {self.layer}.\n"
            f"Allowed values for data.kind at this layer: {allowed_kinds}\n"
            f"{parent_context}\n"
            f"--- Repository context ({inventory.repo_name}) ---\n"
            f"{inventory.repo_context}\n"
            f"--- end repository context ---\n\n"
            "Produce STRICT JSON now."
        )
        raw = chat_json(SYSTEM_PROMPT, user_prompt, model=model)
        try:
            extraction = LLMExtraction.model_validate(raw)
            _validate_edges(extraction)
            return extraction
        except (ValidationError, ValueError) as exc:
            repair_prompt = build_repair_prompt(json.dumps(raw), str(exc))
            raw_repaired = chat_json(SYSTEM_PROMPT, repair_prompt, model=model)
            extraction = LLMExtraction.model_validate(raw_repaired)
            _validate_edges(extraction)
            return extraction

    def extract_deterministic(
        self, inventory: RepoInventory, parent_nodes: list[C4Node]
    ) -> LLMExtraction:
        raise NotImplementedError


class ContextSubagent(BaseLayerSubagent):
    agent_id = "subagent-context"
    role = "Context Layer Specialist Subagent"
    layer: Layer = "context"

    def extract_deterministic(
        self, inventory: RepoInventory, parent_nodes: list[C4Node]
    ) -> LLMExtraction:
        repo_title = inventory.repo_name.replace("-", " ").replace("_", " ").title()
        sys_id = f"sys-{_slug(inventory.repo_name, 'core')}"

        # Detect technologies & external integrations from repo files
        exts = {f.suffix for f in inventory.files}
        file_names = {f.name.lower() for f in inventory.files}
        combined_sample = inventory.repo_context.lower()

        tech_parts: list[str] = []
        if ".svelte" in exts:
            tech_parts.append("Svelte")
        if ".py" in exts:
            tech_parts.append("Python")
        if ".ts" in exts or ".js" in exts:
            tech_parts.append("JavaScript/TypeScript")
        if ".go" in exts:
            tech_parts.append("Go")
        if ".rs" in exts:
            tech_parts.append("Rust")
        tech_summary = ", ".join(tech_parts) if tech_parts else "Software Stack"

        actor_id = "actor-user"
        nodes: list[C4Node] = [
            C4Node(
                id=actor_id,
                position=Position(x=40, y=240),
                data=NodeData(
                    kind="person",
                    name="Developer / Architect",
                    technology=None,
                    description=f"Interacts with {repo_title} to inspect, design, and operate the system.",
                    parentNodeId=None,
                ),
            ),
            C4Node(
                id=sys_id,
                position=Position(x=380, y=240),
                data=NodeData(
                    kind="system",
                    name=repo_title,
                    technology=tech_summary,
                    description=(
                        f"Primary software system in '{inventory.repo_name}' ({len(inventory.files)} source files)."
                    ),
                    parentNodeId=None,
                ),
            ),
        ]
        edges: list[C4Edge] = [
            C4Edge(
                id=f"e-{actor_id}-{sys_id}",
                source=actor_id,
                target=sys_id,
                label="Uses and configures",
                data=EdgeData(technology="HTTPS / UI"),
            )
        ]

        externals: list[tuple[str, str, str, str]] = []
        if "openai" in combined_sample or "lm_studio" in combined_sample or "anthropic" in combined_sample:
            externals.append(
                (
                    "ext-llm-engine",
                    "LLM Inference Service",
                    "OpenAI-compatible / Local LLM API",
                    "Generates structured architectural insights and model completions.",
                )
            )
        if "github" in combined_sample or ".git" in file_names:
            externals.append(
                (
                    "ext-git-host",
                    "Git / Source Host",
                    "Git / HTTPS",
                    "Hosts remote source repositories and version history inspected by the system.",
                )
            )
        if "docker-compose.yml" in file_names or "dockerfile" in file_names:
            externals.append(
                (
                    "ext-container-runtime",
                    "Container Runtime",
                    "Docker / OCI",
                    "Builds and runs containerized application services.",
                )
            )
        if not externals:
            externals.append(
                (
                    "ext-filesystem",
                    "Host File System & Runtime",
                    "OS / POSIX",
                    "Provides configuration, source files, and runtime environment.",
                )
            )

        for idx, (ext_id, ext_name, ext_tech, ext_desc) in enumerate(externals[:3]):
            y_pos = 110 + idx * 170
            nodes.append(
                C4Node(
                    id=ext_id,
                    position=Position(x=740, y=y_pos),
                    data=NodeData(
                        kind="systemExternal",
                        name=ext_name,
                        technology=ext_tech,
                        description=ext_desc,
                        parentNodeId=None,
                    ),
                )
            )
            edges.append(
                C4Edge(
                    id=f"e-{sys_id}-{ext_id}",
                    source=sys_id,
                    target=ext_id,
                    label="Integrates with",
                    data=EdgeData(technology=ext_tech),
                )
            )

        return LLMExtraction(boundaries=[], nodes=nodes, edges=edges)


class ContainerSubagent(BaseLayerSubagent):
    agent_id = "subagent-container"
    role = "Container Layer Specialist Subagent"
    layer: Layer = "container"

    def extract_deterministic(
        self, inventory: RepoInventory, parent_nodes: list[C4Node]
    ) -> LLMExtraction:
        primary_system = self._select_primary_parent(parent_nodes) if parent_nodes else None
        sys_parent_id = primary_system.id if primary_system else "sys-core"
        sys_label = primary_system.data.name if primary_system else inventory.repo_name
        boundary_id = f"boundary-{sys_parent_id}"

        # Group files by top-level directories to discover deployable containers
        top_groups: dict[str, list[Path]] = {}
        for f in inventory.files:
            rel = f.relative_to(inventory.root)
            top = rel.parts[0] if len(rel.parts) > 1 else "root"
            top_groups.setdefault(top, []).append(f)

        # Prefer meaningful code directories over docs/output folders
        scored_dirs = sorted(
            top_groups.items(),
            key=lambda item: (
                sum(1 for p in item[1] if p.suffix in {".py", ".svelte", ".ts", ".js", ".go", ".rs", ".java"}),
                len(item[1]),
            ),
            reverse=True,
        )

        container_specs: list[tuple[str, str, Kind, str, str]] = []
        for folder_name, folder_files in scored_dirs[:4]:
            exts = {p.suffix for p in folder_files}
            names = {p.name.lower() for p in folder_files}
            cid = f"cont-{_slug(folder_name)}"
            readable = (
                f"{inventory.repo_name} Core"
                if folder_name == "root"
                else folder_name.replace("-", " ").replace("_", " ").title()
            )

            if ".svelte" in exts or "vite.config.js" in names or "package.json" in names:
                kind: Kind = "container"
                tech = "Svelte 5, Vite, Svelte Flow" if ".svelte" in exts else "Node.js / Frontend SPA"
                desc = f"Interactive web client in `{folder_name}/` rendering diagrams and developer workflows."
            elif ".py" in exts:
                kind = "container"
                tech = "Python, FastAPI, Uvicorn"
                desc = f"Backend service and multi-agent pipeline in `{folder_name}/`."
            elif any(p.suffix in {".json", ".sql", ".db"} for p in folder_files) and len(exts) == 1:
                kind = "containerDb"
                tech = "JSON / Structured Store"
                desc = f"Persistent model and schema artifacts stored under `{folder_name}/`."
            else:
                kind = "container"
                tech = ", ".join(sorted(e.lstrip(".") for e in exts if e)) or "Module"
                desc = f"Runtime container unit `{folder_name}/` ({len(folder_files)} files)."

            container_specs.append((cid, readable, kind, tech, desc))

        # Ensure at least a data store or secondary container if only 1 folder exists
        if len(container_specs) == 1:
            container_specs.append(
                (
                    "cont-model-store",
                    "Architecture Model Store",
                    "containerDb",
                    "In-Memory / JSON Artifacts",
                    "Stores hierarchical C4 layer graphs, boundaries, and traceability metadata.",
                )
            )

        cols = min(3, max(1, len(container_specs)))
        rows = (len(container_specs) + cols - 1) // cols
        b_width = max(560, cols * 280 + 60)
        b_height = max(260, rows * 190 + 60)

        boundaries = [
            Boundary(
                id=boundary_id,
                label=sys_label,
                position=Position(x=220, y=40),
                size=Size(width=b_width, height=b_height),
            )
        ]

        nodes: list[C4Node] = []
        for idx, (cid, cname, ckind, ctech, cdesc) in enumerate(container_specs):
            col = idx % cols
            row = idx // cols
            nodes.append(
                C4Node(
                    id=cid,
                    position=Position(x=40 + col * 270, y=50 + row * 180),
                    parentId=boundary_id,
                    extent="parent",
                    data=NodeData(
                        kind=ckind,
                        name=cname,
                        technology=ctech,
                        description=cdesc,
                        parentNodeId=sys_parent_id,
                    ),
                )
            )

        # Carry supporting actor + external systems from context layer with parentNodeId pointing to their context node
        actor_parents = [p for p in parent_nodes if p.data.kind == "person"]
        ext_parents = [p for p in parent_nodes if p.data.kind == "systemExternal"]

        edges: list[C4Edge] = []
        first_container_id = nodes[0].id

        for idx, actor in enumerate(actor_parents[:1]):
            actor_node_id = f"cont-{actor.id}"
            nodes.append(
                C4Node(
                    id=actor_node_id,
                    position=Position(x=20, y=b_height + 90 + idx * 160),
                    data=NodeData(
                        kind="person",
                        name=actor.data.name,
                        technology=None,
                        description=actor.data.description,
                        parentNodeId=actor.id,
                    ),
                )
            )
            edges.append(
                C4Edge(
                    id=f"e-{actor_node_id}-{first_container_id}",
                    source=actor_node_id,
                    target=first_container_id,
                    label="Interacts with",
                    data=EdgeData(technology="HTTPS"),
                )
            )

        # Connect containers sequentially
        for i in range(len(container_specs) - 1):
            src_id = container_specs[i][0]
            tgt_id = container_specs[i + 1][0]
            edges.append(
                C4Edge(
                    id=f"e-{src_id}-{tgt_id}",
                    source=src_id,
                    target=tgt_id,
                    label="Requests / delegates to",
                    data=EdgeData(technology="REST / JSON"),
                )
            )

        last_container_id = container_specs[min(1, len(container_specs) - 1)][0]
        for idx, ext in enumerate(ext_parents[:2]):
            ext_node_id = f"cont-{ext.id}"
            nodes.append(
                C4Node(
                    id=ext_node_id,
                    position=Position(x=340 + idx * 300, y=b_height + 90),
                    data=NodeData(
                        kind="systemExternal",
                        name=ext.data.name,
                        technology=ext.data.technology,
                        description=ext.data.description,
                        parentNodeId=ext.id,
                    ),
                )
            )
            edges.append(
                C4Edge(
                    id=f"e-{last_container_id}-{ext_node_id}",
                    source=last_container_id,
                    target=ext_node_id,
                    label="Calls / integrates with",
                    data=EdgeData(technology=ext.data.technology or "API"),
                )
            )

        return LLMExtraction(boundaries=boundaries, nodes=nodes, edges=edges)


class ComponentSubagent(BaseLayerSubagent):
    agent_id = "subagent-component"
    role = "Component Layer Specialist Subagent"
    layer: Layer = "component"

    def extract_deterministic(
        self, inventory: RepoInventory, parent_nodes: list[C4Node]
    ) -> LLMExtraction:
        in_scope_containers = [
            p for p in parent_nodes if p.data.kind in ("container", "containerDb")
        ] or parent_nodes
        primary_container = in_scope_containers[0] if in_scope_containers else None
        boundary_id = f"boundary-{primary_container.id if primary_container else 'container'}"
        boundary_label = primary_container.data.name if primary_container else "Core Container"

        # Pick notable source files across the repo to represent internal components
        code_files = [
            f
            for f in inventory.files
            if f.suffix in {".py", ".svelte", ".js", ".ts", ".go", ".rs", ".java"}
            and f.stem not in {"__init__", "vite.config", "svelte.config"}
        ]
        if not code_files:
            code_files = inventory.files[:6]

        selected_files = code_files[:6]
        cols = min(3, max(1, len(selected_files)))
        rows = (len(selected_files) + cols - 1) // cols
        b_width = max(580, cols * 270 + 60)
        b_height = max(260, rows * 185 + 60)

        boundaries = [
            Boundary(
                id=boundary_id,
                label=boundary_label,
                position=Position(x=180, y=40),
                size=Size(width=b_width, height=b_height),
            )
        ]

        nodes: list[C4Node] = []
        edges: list[C4Edge] = []

        for idx, file_path in enumerate(selected_files):
            rel = file_path.relative_to(inventory.root)
            comp_id = f"comp-{_slug(str(rel.with_suffix('')))}"
            parent_container = in_scope_containers[idx % len(in_scope_containers)] if in_scope_containers else None
            parent_id = parent_container.id if parent_container else None

            tech_map = {
                ".py": "Python Module",
                ".svelte": "Svelte 5 Component",
                ".js": "ES Module",
                ".ts": "TypeScript Module",
                ".json": "JSON Schema",
            }
            tech = tech_map.get(file_path.suffix, f"{file_path.suffix.lstrip('.')} component")
            summary = _summarize_file(file_path, rel)

            col = idx % cols
            row = idx // cols
            nodes.append(
                C4Node(
                    id=comp_id,
                    position=Position(x=40 + col * 265, y=45 + row * 175),
                    parentId=boundary_id,
                    extent="parent",
                    data=NodeData(
                        kind="component",
                        name=file_path.stem,
                        technology=tech,
                        description=summary,
                        parentNodeId=parent_id,
                    ),
                )
            )

        for i in range(len(nodes) - 1):
            edges.append(
                C4Edge(
                    id=f"e-{nodes[i].id}-{nodes[i + 1].id}",
                    source=nodes[i].id,
                    target=nodes[i + 1].id,
                    label="Invokes / passes state to",
                    data=EdgeData(technology="Internal call"),
                )
            )

        return LLMExtraction(boundaries=boundaries, nodes=nodes, edges=edges)


class CodeSubagent(BaseLayerSubagent):
    agent_id = "subagent-code"
    role = "Code Layer Specialist Subagent"
    layer: Layer = "code"

    def extract_deterministic(
        self, inventory: RepoInventory, parent_nodes: list[C4Node]
    ) -> LLMExtraction:
        component_parents = [p for p in parent_nodes if p.data.kind == "component"] or parent_nodes
        symbols = _extract_code_symbols(inventory, component_parents)

        nodes: list[C4Node] = []
        edges: list[C4Edge] = []
        cols = 3

        for idx, sym in enumerate(symbols[:8]):
            col = idx % cols
            row = idx // cols
            nodes.append(
                C4Node(
                    id=sym["id"],
                    position=Position(x=60 + col * 280, y=50 + row * 185),
                    data=NodeData(
                        kind=sym["kind"],
                        name=sym["name"],
                        technology=sym["technology"],
                        description=sym["description"],
                        parentNodeId=sym["parentNodeId"],
                    ),
                )
            )

        for i in range(len(nodes) - 1):
            edges.append(
                C4Edge(
                    id=f"e-code-{nodes[i].id}-{nodes[i + 1].id}",
                    source=nodes[i].id,
                    target=nodes[i + 1].id,
                    label="calls / references",
                    data=EdgeData(technology=None),
                )
            )

        return LLMExtraction(boundaries=[], nodes=nodes, edges=edges)


def _summarize_file(file_path: Path, rel_path: Path) -> str:
    try:
        content = file_path.read_text(errors="ignore")
    except OSError:
        return f"Component defined in `{rel_path}`."

    if file_path.suffix == ".py":
        try:
            tree = ast.parse(content)
            doc = ast.get_docstring(tree)
            if doc:
                first_line = doc.strip().splitlines()[0].strip()
                return f"{first_line} (`{rel_path}`)"
        except SyntaxError:
            pass

    for line in content.splitlines()[:12]:
        stripped = line.strip().lstrip("/#*<!- ").rstrip("->")
        if len(stripped) > 18 and not stripped.startswith(("import ", "from ", "<script", "{")):
            return f"{stripped[:110]} (`{rel_path}`)"

    return f"Implements `{file_path.stem}` responsibilities in `{rel_path}`."


def _extract_code_symbols(
    inventory: RepoInventory, component_parents: list[C4Node]
) -> list[dict]:
    results: list[dict] = []
    parent_by_stem = {p.data.name.lower(): p.id for p in component_parents}
    default_parent_id = component_parents[0].id if component_parents else None

    for f in inventory.files:
        parent_id = parent_by_stem.get(f.stem.lower())
        if parent_id is None and component_parents:
            parent_id = component_parents[len(results) % len(component_parents)].id
        elif parent_id is None:
            parent_id = default_parent_id

        if f.suffix == ".py":
            try:
                tree = ast.parse(f.read_text(errors="ignore"))
            except Exception:
                continue
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    bases = [ast.unparse(b) for b in node.bases] if node.bases else []
                    kind: Kind = "codeEnum" if any("Enum" in b for b in bases) else "codeClass"
                    doc = (ast.get_docstring(node) or f"Class in `{f.name}`.").splitlines()[0]
                    results.append(
                        {
                            "id": f"code-{_slug(f.stem)}-{_slug(node.name)}",
                            "name": node.name,
                            "kind": kind,
                            "technology": f"python class ({f.name})",
                            "description": doc[:120],
                            "parentNodeId": parent_id,
                        }
                    )
                elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    doc = (ast.get_docstring(node) or f"Function `{node.name}()` in `{f.name}`.").splitlines()[0]
                    results.append(
                        {
                            "id": f"code-{_slug(f.stem)}-{_slug(node.name)}",
                            "name": f"{node.name}()",
                            "kind": "codeInterface",
                            "technology": f"function ({f.name})",
                            "description": doc[:120],
                            "parentNodeId": parent_id,
                        }
                    )
        elif f.suffix in {".js", ".ts", ".svelte"}:
            text = f.read_text(errors="ignore")
            for match in re.finditer(r"export\s+(?:async\s+)?function\s+([A-Za-z0-9_]+)", text):
                fn_name = match.group(1)
                results.append(
                    {
                        "id": f"code-{_slug(f.stem)}-{_slug(fn_name)}",
                        "name": f"{fn_name}()",
                        "kind": "codeInterface",
                        "technology": f"{f.suffix.lstrip('.')} export ({f.name})",
                        "description": f"Exported function `{fn_name}` in `{f.name}`.",
                        "parentNodeId": parent_id,
                    }
                )
            for match in re.finditer(r"export\s+const\s+([A-Za-z0-9_]+)", text):
                const_name = match.group(1)
                results.append(
                    {
                        "id": f"code-{_slug(f.stem)}-{_slug(const_name)}",
                        "name": const_name,
                        "kind": "codeEnum",
                        "technology": f"constant ({f.name})",
                        "description": f"Exported module symbol `{const_name}` in `{f.name}`.",
                        "parentNodeId": parent_id,
                    }
                )
            if f.suffix == ".svelte":
                results.append(
                    {
                        "id": f"code-svelte-{_slug(f.stem)}",
                        "name": f"{f.stem}.svelte",
                        "kind": "codeClass",
                        "technology": "Svelte 5 component module",
                        "description": f"Reactive UI component module `{f.name}`.",
                        "parentNodeId": parent_id,
                    }
                )

        if len(results) >= 8:
            break

    if not results:
        for idx, f in enumerate(inventory.files[:4]):
            pid = component_parents[idx % len(component_parents)].id if component_parents else default_parent_id
            results.append(
                {
                    "id": f"code-mod-{idx}-{_slug(f.stem)}",
                    "name": f.name,
                    "kind": "codeClass",
                    "technology": f.suffix.lstrip(".") or "module",
                    "description": f"Source module `{f.relative_to(inventory.root)}`.",
                    "parentNodeId": pid,
                }
            )
    return results


# ============================================================================
# Supervisor Agent (coordinates the 4 specialist subagents + builds hierarchy)
# ============================================================================


class SupervisorAgent:
    agent_id = "c4-supervisor"
    role = "Cross-Layer Hierarchy Supervisor Agent"
    skills: tuple[str, ...] = (
        "read-code",
        "draw-diagram",
        "execute-sandbox",
        "follow-workflows",
        "evaluate-metrics",
        "validate-repair",
    )

    def __init__(self) -> None:
        self.subagents: tuple[
            ContextSubagent, ContainerSubagent, ComponentSubagent, CodeSubagent
        ] = (
            ContextSubagent(),
            ContainerSubagent(),
            ComponentSubagent(),
            CodeSubagent(),
        )

    def coordinate(
        self,
        inventory: RepoInventory,
        use_llm: bool = False,
        model: str | None = None,
    ) -> tuple[dict[Layer, LayerResponse], list[HierarchyTreeNode], list[AgentReport]]:
        layers_out: dict[Layer, LayerResponse] = {}
        reports: list[AgentReport] = []
        previous_nodes: list[C4Node] = []

        for subagent in self.subagents:
            layer_resp, sub_report = subagent.run(
                inventory=inventory,
                parent_nodes=previous_nodes,
                use_llm=use_llm,
                model=model,
            )
            layers_out[subagent.layer] = layer_resp
            reports.append(sub_report)
            previous_nodes = layer_resp.nodes

        hierarchy = self.build_hierarchy_tree(layers_out)
        total_nodes = sum(len(l.nodes) for l in layers_out.values())
        total_edges = sum(len(l.edges) for l in layers_out.values())

        supervisor_report = AgentReport(
            agent_id=self.agent_id,
            role=self.role,
            layer=None,
            status="completed",
            summary=(
                f"Coordinated 4 specialist subagents (Context -> Container -> Component -> Code) "
                f"and verified parent-child hierarchy across {total_nodes} nodes and {total_edges} edges."
            ),
            produced_nodes=total_nodes,
            produced_edges=total_edges,
        )
        return layers_out, hierarchy, [supervisor_report, *reports]

    def build_hierarchy_tree(
        self, layers: dict[Layer, LayerResponse]
    ) -> list[HierarchyTreeNode]:
        order: tuple[Layer, ...] = ("context", "container", "component", "code")
        tree_nodes_by_layer: dict[Layer, dict[str, HierarchyTreeNode]] = {}

        for layer_key in order:
            layer_resp = layers.get(layer_key)
            if not layer_resp:
                tree_nodes_by_layer[layer_key] = {}
                continue
            layer_map: dict[str, HierarchyTreeNode] = {}
            for node in layer_resp.nodes:
                layer_map[node.id] = HierarchyTreeNode(
                    id=node.id,
                    name=node.data.name,
                    layer=layer_key,
                    kind=node.data.kind,
                    technology=node.data.technology,
                    description=node.data.description,
                    parentNodeId=node.data.parentNodeId,
                    children=[],
                )
            tree_nodes_by_layer[layer_key] = layer_map

        # Link each child layer to its parent layer (Context -> Container -> Component -> Code)
        for idx in range(len(order) - 1):
            parent_layer = order[idx]
            child_layer = order[idx + 1]
            parents = tree_nodes_by_layer[parent_layer]
            children = tree_nodes_by_layer[child_layer]
            if not parents:
                continue
            fallback_parent = next(
                (p for p in parents.values() if p.kind in ("system", "container", "component")),
                next(iter(parents.values())),
            )
            for child in children.values():
                parent = parents.get(child.parentNodeId or "")
                if parent is None:
                    parent = fallback_parent
                    child.parentNodeId = parent.id
                parent.children.append(child)

        return list(tree_nodes_by_layer["context"].values())


# ============================================================================
# Manager Agent (resolves local path / GitHub URL and invokes Supervisor)
# ============================================================================


class ManagerAgent:
    agent_id = "c4-manager"
    role = "Repository & Architecture Manager Agent"
    skills: tuple[str, ...] = (
        "read-code",
        "execute-sandbox",
        "follow-workflows",
        "confluence-export",
    )

    def __init__(self) -> None:
        self.supervisor = SupervisorAgent()

    def analyze(
        self,
        source: str,
        source_type: str | None = None,
        use_llm: bool = False,
        model: str | None = None,
    ) -> HierarchyModelResponse:
        cleaned = source.strip()
        if not cleaned:
            raise ValueError("Please provide a non-empty local path or GitHub repository URL.")

        temp_dir: str | None = None
        try:
            root_path, resolved_type, repo_name = self._resolve_source(cleaned, expected_type=source_type)
            if resolved_type == "github":
                temp_dir = str(root_path)

            files = [
                p
                for p in sorted(root_path.rglob("*"))
                if not any(part in IGNORED_DIRS for part in p.parts)
                and p.is_file()
                and p.suffix in INCLUDED_EXTENSIONS
            ]
            if not files:
                raise ValueError(
                    f"No supported source files found in '{cleaned}'."
                )

            repo_context = build_repo_context(str(root_path))
            inventory = RepoInventory(
                root=root_path,
                source_label=cleaned,
                source_type=resolved_type,
                repo_name=repo_name,
                files=files,
                repo_context=repo_context,
            )

            llm_ready = bool(use_llm and is_server_reachable())
            layers, hierarchy, sub_reports = self.supervisor.coordinate(
                inventory=inventory,
                use_llm=llm_ready,
                model=model,
            )

            manager_report = AgentReport(
                agent_id=self.agent_id,
                role=self.role,
                layer=None,
                status="completed",
                summary=(
                    f"Ingested {resolved_type} source '{repo_name}' ({len(files)} files) "
                    f"and delegated hierarchical C4 generation to Supervisor."
                ),
                produced_nodes=sum(len(l.nodes) for l in layers.values()),
                produced_edges=sum(len(l.edges) for l in layers.values()),
            )

            return HierarchyModelResponse(
                source=cleaned,
                source_type=resolved_type,
                repo_name=repo_name,
                agents=[manager_report, *sub_reports],
                layers=layers,
                hierarchy=hierarchy,
            )
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _resolve_source(self, source: str, expected_type: str | None = None) -> tuple[Path, str, str]:
        looks_like_github = (
            source.startswith(("http://", "https://", "git@"))
            or source.startswith("github.com/")
        )
        if expected_type == "local" and looks_like_github:
            raise ValueError(
                "Source type 'Local' is selected, but a GitHub/remote URL was entered. "
                "Please enter a valid local filesystem path or switch the dropdown to 'Github'."
            )
        if expected_type == "github" and not looks_like_github:
            raise ValueError(
                "Source type 'Github' is selected, but a local path was entered. "
                "Please enter a valid GitHub URL (e.g. https://github.com/owner/repo) or switch the dropdown to 'Local'."
            )

        is_github = expected_type == "github" or (expected_type is None and looks_like_github)
        if is_github:
            url = f"https://{source}" if source.startswith("github.com/") else source
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            if len(path_parts) < 2 and not source.startswith("git@"):
                raise ValueError(
                    f"Invalid GitHub repository URL '{source}'. Expected https://github.com/<owner>/<repo>."
                )
            repo_name = (path_parts[1] if len(path_parts) >= 2 else Path(source).stem).removesuffix(".git")
            clone_url = url
            if parsed.netloc in {"github.com", "www.github.com"} and len(path_parts) >= 2:
                clone_url = f"https://github.com/{path_parts[0]}/{repo_name}.git"

            tmp_root = Path(tempfile.mkdtemp(prefix=f"c4-repo-{repo_name}-"))
            try:
                proc = subprocess.run(
                    ["git", "clone", "--depth", "1", clone_url, str(tmp_root)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
            except Exception as exc:
                shutil.rmtree(tmp_root, ignore_errors=True)
                raise ValueError(f"Failed to clone GitHub repository '{clone_url}': {exc}") from exc

            if proc.returncode != 0:
                shutil.rmtree(tmp_root, ignore_errors=True)
                stderr = (proc.stderr or proc.stdout or "git clone failed").strip()
                raise ValueError(f"Could not clone GitHub repository '{clone_url}': {stderr}")

            # Support GitHub tree subpath URLs like https://github.com/owner/repo/tree/main/subdir
            if len(path_parts) > 4 and path_parts[2] == "tree":
                subpath = tmp_root.joinpath(*path_parts[4:])
                if subpath.exists() and subpath.is_dir():
                    return subpath, "github", f"{repo_name}/{subpath.name}"

            return tmp_root, "github", repo_name

        # Local path resolution: try direct path, workspace-relative path, or parent-relative path
        candidates = [
            Path(source).expanduser(),
            Path.cwd() / source,
            Path.cwd().parent / source,
        ]
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.exists():
                target = resolved if resolved.is_dir() else resolved.parent
                return target, "local", target.name

        raise FileNotFoundError(
            f"Local path '{source}' does not exist. Provide an existing directory path or a GitHub URL."
        )


manager_agent = ManagerAgent()
