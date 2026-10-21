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

Each agent is bound to its own Pfizer LLMHub adapter (see ``config/llmhub.yaml``):

- Manager / Supervisor use the **powerful** model tier.
- Specialist layer subagents use the **medium** model tier plus a lightweight
  SQLite experience DB that stores prior code-reading experiences to refine
  deciphering on repeat repository analyses.

When LLMHub is unreachable (or ``use_llm`` is false), specialists fall back to
deterministic AST / source-tree static analysis so the pipeline always succeeds.
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
from app.experience_store import ExperienceStore, fingerprint_repo
from app.llmhub_adapter import LLMHubAdapter, get_adapter, is_hub_reachable
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

    def __init__(self) -> None:
        self.adapter: LLMHubAdapter = get_adapter(self.agent_id)
        exp_path = self.adapter.experience_db
        self.experience_store: ExperienceStore | None = (
            ExperienceStore(exp_path, layer=self.layer) if exp_path else None
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
        target_model = model or self.adapter.model

        if use_llm:
            try:
                extraction = self._extract_via_llm(inventory, parent_nodes, target_model)
                summary_suffix = (
                    f"LLMHub {self.adapter.tier}/{target_model}"
                )
            except Exception as exc:
                logger.warning(
                    "[%s] LLMHub extraction failed (%s); falling back to static source analysis.",
                    self.agent_id,
                    exc,
                )

        if extraction is None:
            extraction = self.extract_deterministic(inventory, parent_nodes)

        extraction = self._ensure_parent_links(extraction, parent_nodes)

        if self.experience_store is not None:
            try:
                rel_paths = [
                    str(p.relative_to(inventory.root))
                    if p.is_relative_to(inventory.root)
                    else str(p)
                    for p in inventory.files
                ]
                fp = fingerprint_repo(inventory.repo_name, rel_paths)
                self.experience_store.remember_from_extraction(
                    repo_fingerprint=fp,
                    repo_name=inventory.repo_name,
                    extraction=extraction,
                )
            except Exception as exc:  # noqa: BLE001 — experience DB must never fail the pipeline
                logger.debug("[%s] experience store write skipped: %s", self.agent_id, exc)

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
            return f"Business Reference Context · {inventory.repo_name}"
        if self.layer == "container":
            sys_nodes = [p for p in parent_nodes if p.data.kind == "system"]
            return f"Zoomed into {len(sys_nodes) or 1} Business Contexts · All Containers Opened Up"
        if self.layer == "component":
            cont_nodes = [p for p in parent_nodes if p.data.kind in ("container", "containerDb")]
            names = ", ".join(c.data.name.split("—")[0].strip() for c in cont_nodes[:5])
            return f"Zoomed into All {len(cont_nodes)} Containers ({names})"
        if self.layer == "code":
            comp_nodes = [p for p in parent_nodes if p.data.kind == "component"]
            return f"Zoomed into {len(comp_nodes)} Components · Code & Type Symbols Opened Up"
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

        experience_block = ""
        if self.experience_store is not None:
            rel_paths = [
                str(p.relative_to(inventory.root))
                if p.is_relative_to(inventory.root)
                else str(p)
                for p in inventory.files
            ]
            fp = fingerprint_repo(inventory.repo_name, rel_paths)
            experience_block = self.experience_store.recall_as_prompt_block(fp)

        user_prompt = (
            f"You are specialist subagent `{self.agent_id}` ({self.role}) for C4 layer: {self.layer}.\n"
            f"LLMHub adapter tier: {self.adapter.tier} · model: {model or self.adapter.model}\n"
            f"Allowed values for data.kind at this layer: {allowed_kinds}\n"
            f"{parent_context}\n"
            f"{experience_block}"
            f"--- Repository context ({inventory.repo_name}) ---\n"
            f"{inventory.repo_context}\n"
            f"--- end repository context ---\n\n"
            "Produce STRICT JSON now."
        )
        raw = self.adapter.chat_json(SYSTEM_PROMPT, user_prompt, model=model)
        try:
            extraction = LLMExtraction.model_validate(raw)
            _validate_edges(extraction)
            return extraction
        except (ValidationError, ValueError) as exc:
            repair_prompt = build_repair_prompt(json.dumps(raw), str(exc))
            raw_repaired = self.adapter.chat_json(
                SYSTEM_PROMPT, repair_prompt, model=model
            )
            extraction = LLMExtraction.model_validate(raw_repaired)
            _validate_edges(extraction)
            return extraction

    def extract_deterministic(
        self, inventory: RepoInventory, parent_nodes: list[C4Node]
    ) -> LLMExtraction:
        raise NotImplementedError


# ============================================================================
# Repository Domain & Container Discovery Helpers
# ============================================================================

CODE_EXTS = {
    ".py",
    ".svelte",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".sql",
}

NON_CONTAINER_DIRS = {
    ".github",
    ".claude",
    ".cursor",
    "e2e",
    "test",
    "tests",
    "__tests__",
    "docs",
    "documentation",
    "vendor",
    "claude_output",
}


@dataclass
class ContainerProfile:
    scope_key: str  # e.g. "app", "components", "lib", "hooks,contexts", "supabase,migrations"
    folder_names: list[str]
    files: list[Path]
    container_id: str
    container_name: str
    container_kind: Kind
    container_tech: str
    container_desc: str
    business_id: str
    business_name: str
    business_tech: str
    business_desc: str
    sub_domains: list[str]


def _humanize_token(token: str) -> str:
    cleaned = token.strip("()[]{}_- /")
    if not cleaned:
        return "Core"
    special = {
        "api": "API",
        "ui": "UI",
        "db": "Database",
        "rls": "RLS",
        "sso": "SSO",
        "llm": "LLM",
        "ai": "AI",
        "pods": "PODs",
        "pod": "POD",
        "auth": "Auth",
        "rbac": "RBAC",
        "c4": "C4",
        "spa": "SPA",
        "authcontext": "AuthContext",
    }
    words = [w for w in re.split(r"[-_\s/()\[\]{}]+", cleaned) if w]
    if len(words) > 1 and words[0].lower() == "app":
        words = words[1:]
    return " ".join(special.get(w.lower(), w.capitalize()) for w in words if w)


def _extract_readme_summary(root: Path, repo_title: str) -> str:
    for candidate in ("README.md", "docs/USER_GUIDE.md", "CLAUDE.md", "AGENTS.md"):
        p = root / candidate
        if not p.exists():
            continue
        try:
            lines = p.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for line in lines:
            s = line.strip()
            if (
                not s
                or s.startswith("#")
                or s.startswith("<!--")
                or s.startswith(">")
                or s.startswith("📘")
                or s.startswith("|")
                or s.startswith("```")
                or len(s) < 35
            ):
                continue
            clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
            clean = re.sub(r"[`*_]", "", clean).strip()
            if len(clean) >= 35:
                return clean[:200]
    return f"Enterprise software system and domain capabilities implemented in {repo_title}."


def _discover_container_profiles(inventory: RepoInventory) -> list[ContainerProfile]:
    top_groups: dict[str, list[Path]] = {}
    for f in inventory.files:
        rel = f.relative_to(inventory.root)
        top = rel.parts[0] if len(rel.parts) > 1 else "root"
        top_groups.setdefault(top, []).append(f)

    # Merge closely paired architectural directories so all key containers are preserved cleanly
    merged_groups: list[tuple[list[str], list[Path]]] = []
    consumed: set[str] = set()

    if "hooks" in top_groups and "contexts" in top_groups:
        merged_groups.append((["hooks", "contexts"], top_groups["hooks"] + top_groups["contexts"]))
        consumed.update({"hooks", "contexts"})

    if "supabase" in top_groups and "migrations" in top_groups:
        merged_groups.append(
            (["supabase", "migrations"], top_groups["supabase"] + top_groups["migrations"])
        )
        consumed.update({"supabase", "migrations"})

    for folder, files in top_groups.items():
        if folder in consumed or folder in NON_CONTAINER_DIRS:
            continue
        if folder == "root" and len(top_groups) > 1:
            continue
        merged_groups.append(([folder], files))

    if not merged_groups:
        for folder, files in top_groups.items():
            merged_groups.append(([folder], files))

    def _score_group(item: tuple[list[str], list[Path]]) -> tuple[int, int, int]:
        folders, files = item
        code_cnt = sum(
            1
            for p in files
            if p.suffix in CODE_EXTS and not p.name.endswith((".test.ts", ".test.tsx", ".spec.ts"))
        )
        priority = (
            1
            if any(
                f in {"app", "components", "lib", "hooks", "supabase", "types", "frontend", "backend", "skills", "src"}
                for f in folders
            )
            else 0
        )
        return (priority, code_cnt, len(files))

    merged_groups.sort(key=_score_group, reverse=True)
    selected_groups = merged_groups[:6]

    profiles: list[ContainerProfile] = []
    for folders, files in selected_groups:
        scope_key = ",".join(folders)
        primary_folder = folders[0]
        exts = {p.suffix for p in files}
        names = {p.name.lower() for p in files}

        # Discover top sub-domains inside this container
        sub_counts: dict[str, int] = {}
        for f in files:
            rel = f.relative_to(inventory.root)
            if len(rel.parts) >= 2:
                sub = rel.parts[1]
                if sub not in {"__tests__", "fixtures", "mocks"} and not sub.startswith("."):
                    sub_counts[sub] = sub_counts.get(sub, 0) + 1
            else:
                stem = f.stem
                sub_counts[stem] = sub_counts.get(stem, 0) + 1

        top_subs = [
            _humanize_token(k)
            for k, _ in sorted(sub_counts.items(), key=lambda x: x[1], reverse=True)
            if not k.endswith(".test") and not k.endswith(".spec")
        ][:5]
        sub_summary = ", ".join(top_subs) if top_subs else "Core Modules"

        cid = f"cont-{_slug('-'.join(folders))}"
        biz_id = f"sys-biz-{_slug('-'.join(folders))}"
        folder_badge = " + ".join(f"`{d}/`" for d in folders)

        if primary_folder == "app":
            ckind: Kind = "container"
            cname = "App — Next.js App Router & API"
            ctech = "Next.js 16, React 19, TypeScript, App Router"
            cdesc = (
                f"Application routing, page views, and server API endpoints in {folder_badge} "
                f"covering {sub_summary} ({len(files)} files)."
            )
            bname = "Workspace Portal & API Experience Context"
            btech = f"Business Reference → {folder_badge}"
            bdesc = (
                f"High-level business workflows and user-facing screens ({sub_summary}) "
                f"delivered through the {folder_badge} container."
            )
        elif primary_folder == "components":
            ckind = "container"
            cname = "Components — Domain UI & Feature Suite"
            ctech = "React 19, Radix UI, Tailwind CSS, TypeScript"
            cdesc = (
                f"Interactive domain UI components and feature workflows in {folder_badge} "
                f"for {sub_summary} ({len(files)} files)."
            )
            bname = "Interactive Domain Workflows & UI Context"
            btech = f"Business Reference → {folder_badge}"
            bdesc = (
                f"Business capability views, editors, and visual dashboards ({sub_summary}) "
                f"worked on top of the {folder_badge} container."
            )
        elif primary_folder == "lib":
            ckind = "container"
            cname = "Lib — Domain Services, AI Agent & Queries"
            ctech = "TypeScript, Vercel AI SDK, Drizzle ORM, Langfuse"
            cdesc = (
                f"Core domain logic, AI assistant orchestration, data queries, and bulk processing "
                f"in {folder_badge} ({sub_summary}, {len(files)} files)."
            )
            bname = "Core Domain Intelligence, AI & Bulk Operations Context"
            btech = f"Business Reference → {folder_badge}"
            bdesc = (
                f"Business rules, AI assistant intelligence, bulk data operations, and domain query "
                f"capabilities ({sub_summary}) worked on top of {folder_badge}."
            )
        elif primary_folder in {"hooks", "contexts"}:
            ckind = "container"
            cname = "Hooks & Contexts — State, Auth & Queries"
            ctech = "TanStack React Query, React Context, TypeScript"
            cdesc = (
                f"Client data synchronization hooks, mutations, and RBAC authentication context "
                f"in {folder_badge} ({sub_summary}, {len(files)} files)."
            )
            bname = "Client State Sync, Role Access & Session Context"
            btech = f"Business Reference → {folder_badge}"
            bdesc = (
                f"Role-based access control (Viewer/Editor/Admin), live query synchronization, and "
                f"mutation workflows ({sub_summary}) on top of {folder_badge}."
            )
        elif primary_folder in {"supabase", "migrations", "db"}:
            ckind = "containerDb"
            cname = "Supabase & Migrations — Postgres, RLS & Audit"
            ctech = "PostgreSQL, Supabase RLS, SQL Migrations, Edge Functions"
            cdesc = (
                f"Relational schema migrations, Row-Level Security policies, and audit triggers "
                f"in {folder_badge} ({sub_summary}, {len(files)} files)."
            )
            bname = "Enterprise Data Governance, RLS & Audit Context"
            btech = f"Business Reference → {folder_badge}"
            bdesc = (
                f"Data persistence, self-service Row-Level Security enforcement, and immutable "
                f"audit trail governance ({sub_summary}) on top of {folder_badge}."
            )
        elif primary_folder == "types":
            ckind = "container"
            cname = "Types — Domain & Integration Contracts"
            ctech = "TypeScript Declarations & Schemas"
            cdesc = (
                f"Shared domain type contracts and external integration schemas in {folder_badge} "
                f"({sub_summary}, {len(files)} files)."
            )
            bname = "Canonical Domain Schema & Contract Context"
            btech = f"Business Reference → {folder_badge}"
            bdesc = (
                f"Standardized business entity definitions and cross-container data contracts "
                f"({sub_summary}) governing {folder_badge}."
            )
        elif primary_folder == "frontend" or ".svelte" in exts:
            ckind = "container"
            cname = f"{_humanize_token(primary_folder)} — Interactive Web Client"
            ctech = "Svelte 5, Vite, Svelte Flow" if ".svelte" in exts else "React / TypeScript SPA"
            cdesc = (
                f"Interactive web client in {folder_badge} rendering architecture views and "
                f"workflows ({sub_summary}, {len(files)} files)."
            )
            bname = "Interactive Visualization & User Experience Context"
            btech = f"Business Reference → {folder_badge}"
            bdesc = (
                f"Visual exploration, interactive canvas manipulation, and developer inspection "
                f"capabilities ({sub_summary}) worked on top of {folder_badge}."
            )
        elif primary_folder == "backend" or ".py" in exts:
            ckind = "container"
            cname = f"{_humanize_token(primary_folder)} — Multi-Agent API Service"
            ctech = "Python, FastAPI, Pydantic, AST Analyzer"
            cdesc = (
                f"Backend orchestration service and multi-agent analysis pipeline in {folder_badge} "
                f"({sub_summary}, {len(files)} files)."
            )
            bname = "Automated Architecture Extraction & Agent Context"
            btech = f"Business Reference → {folder_badge}"
            bdesc = (
                f"Multi-agent repository intelligence, hierarchical model synthesis, and REST API "
                f"capabilities ({sub_summary}) worked on top of {folder_badge}."
            )
        elif primary_folder == "skills":
            ckind = "containerDb"
            cname = "Skills — Agent Skill Specifications"
            ctech = "SKILL.md Catalog & Guardrail Rules"
            cdesc = (
                f"Declarative agent skills, UX standards, and execution playbooks in {folder_badge} "
                f"({sub_summary}, {len(files)} files)."
            )
            bname = "Reusable AI Skill & Governance Catalog Context"
            btech = f"Business Reference → {folder_badge}"
            bdesc = (
                f"Domain-specific agent capabilities, design heuristics, and verification workflows "
                f"({sub_summary}) governing {folder_badge}."
            )
        else:
            ckind = (
                "containerDb"
                if any(p.suffix in {".sql", ".db"} for p in files)
                else "container"
            )
            readable = (
                f"{inventory.repo_name} Core"
                if primary_folder == "root"
                else " & ".join(_humanize_token(d) for d in folders)
            )
            cname = f"{readable} Container"
            ctech = ", ".join(sorted(e.lstrip(".") for e in exts if e)) or "Runtime Module"
            cdesc = (
                f"Container module in {folder_badge} implementing {sub_summary} ({len(files)} files)."
            )
            bname = f"{readable} Business Capability Context"
            btech = f"Business Reference → {folder_badge}"
            bdesc = (
                f"High-level business capability context for {sub_summary} worked on top of "
                f"the {folder_badge} container."
            )

        profiles.append(
            ContainerProfile(
                scope_key=scope_key,
                folder_names=folders,
                files=files,
                container_id=cid,
                container_name=cname,
                container_kind=ckind,
                container_tech=ctech,
                container_desc=cdesc,
                business_id=biz_id,
                business_name=bname,
                business_tech=btech,
                business_desc=bdesc,
                sub_domains=top_subs,
            )
        )

    return profiles


def _discover_business_personas(inventory: RepoInventory, repo_title: str) -> list[tuple[str, str, str]]:
    sample = inventory.repo_context.lower()
    # Check if repository defines Viewer / Editor / Admin roles (e.g. pod-roster)
    if "viewer" in sample and "editor" in sample and "admin" in sample:
        return [
            (
                "actor-viewer-editor",
                "Viewer & Editor (Team Member / POD Lead)",
                f"Uses {repo_title} to browse PODs, People, Hiring & Matrix, self-manage own profile/assignments, and run bulk roster updates.",
            ),
            (
                "actor-admin",
                "Platform Administrator (Governance & Ops)",
                f"Manages all PODs, people records, RBAC user roles, lookup configurations, and reviews the immutable Audit Log in {repo_title}.",
            ),
        ]
    return [
        (
            "actor-business-user",
            "Product & Domain Stakeholder",
            f"Relies on {repo_title} business capabilities to inspect domain workflows, manage records, and drive operational decisions.",
        ),
        (
            "actor-architect-dev",
            "Software Architect & Engineering Lead",
            f"Designs, evolves, and verifies the multi-layer containers and components powering {repo_title}.",
        ),
    ]


def _discover_external_systems(inventory: RepoInventory) -> list[tuple[str, str, str, str]]:
    sample = inventory.repo_context.lower()
    file_names = {f.name.lower() for f in inventory.files}
    externals: list[tuple[str, str, str, str]] = []

    if "supabase" in sample or any("supabase" in str(f).lower() for f in inventory.files):
        externals.append(
            (
                "ext-supabase-platform",
                "Supabase Data, Auth & RLS Platform",
                "PostgreSQL / Supabase SSR & RLS",
                "Managed PostgreSQL database, Row-Level Security policy engine, and authentication session backend.",
            )
        )
    if "langfuse" in sample or "@ai-sdk" in sample or "openai" in sample or "llmhub" in sample:
        externals.append(
            (
                "ext-ai-llm-hub",
                "LLM Hub & AI Observability",
                "OpenAI-Compatible API / Langfuse",
                "Provides LLM inference for the AI assistant/agents and traces prompt execution telemetry.",
            )
        )
    if "wrangler.jsonc" in file_names or "opennext" in sample or "cloudflare" in sample:
        externals.append(
            (
                "ext-cloudflare-edge",
                "Cloudflare Workers & OpenNext Edge",
                "Cloudflare Workers / Secrets Store",
                "Hosts the edge SSR runtime, worker bindings, and platform secrets store.",
            )
        )
    if "sso" in sample or "saml" in sample or "active-directory" in sample:
        externals.append(
            (
                "ext-enterprise-sso",
                "Enterprise SSO & Directory Service",
                "SAML 2.0 / Active Directory",
                "Authenticates corporate users via Single Sign-On and supplies directory identity attributes.",
            )
        )
    if not externals:
        if "github" in sample or ".git" in file_names:
            externals.append(
                (
                    "ext-git-host",
                    "Git / Source Repository Host",
                    "Git / HTTPS",
                    "Hosts source repositories and version history analyzed by the platform.",
                )
            )
        externals.append(
            (
                "ext-runtime-env",
                "Host Runtime & File System",
                "OS / POSIX Runtime",
                "Provides local file system access, environment configuration, and execution runtime.",
            )
        )
    return externals[:4]


class ContextSubagent(BaseLayerSubagent):
    agent_id = "subagent-context"
    role = "Context Layer Specialist Subagent"
    layer: Layer = "context"

    def extract_deterministic(
        self, inventory: RepoInventory, parent_nodes: list[C4Node]
    ) -> LLMExtraction:
        repo_title = inventory.repo_name.replace("-", " ").replace("_", " ").title()
        profiles = _discover_container_profiles(inventory)
        readme_summary = _extract_readme_summary(inventory.root, repo_title)

        # Create an overarching Business Context boundary that frames the business reference nodes
        cols = min(2, max(1, len(profiles)))
        rows = (len(profiles) + cols - 1) // cols
        b_width = max(560, cols * 285 + 70)
        b_height = max(270, rows * 195 + 100)
        biz_boundary_id = f"boundary-context-{_slug(inventory.repo_name)}"

        boundaries = [
            Boundary(
                id=biz_boundary_id,
                label=f"{repo_title} — Business Reference Context",
                subtitle="Business Capability Map · Worked on Top of Containers & Components",
                description=readme_summary,
                upperLayer="context",
                sourceNodeId=None,
                position=Position(x=310, y=40),
                size=Size(width=b_width, height=b_height),
            )
        ]

        nodes: list[C4Node] = []
        edges: list[C4Edge] = []

        # 1. Business Personas on the left
        personas = _discover_business_personas(inventory, repo_title)
        for idx, (actor_id, actor_name, actor_desc) in enumerate(personas):
            nodes.append(
                C4Node(
                    id=actor_id,
                    position=Position(x=25, y=80 + idx * 210),
                    data=NodeData(
                        kind="person",
                        name=actor_name,
                        technology="Business Persona / Role",
                        description=actor_desc,
                        parentNodeId=None,
                    ),
                )
            )

        # 2. Business Reference System nodes inside the Business Context boundary
        # Each node represents the business context worked on top of the underlying container(s)
        for idx, prof in enumerate(profiles):
            col = idx % cols
            row = idx // cols
            nodes.append(
                C4Node(
                    id=prof.business_id,
                    position=Position(x=35 + col * 275, y=78 + row * 185),
                    parentId=biz_boundary_id,
                    extent="parent",
                    data=NodeData(
                        kind="system",
                        name=prof.business_name,
                        technology=prof.business_tech,
                        description=prof.business_desc,
                        parentNodeId=None,
                        sourceScope=prof.scope_key,
                    ),
                )
            )

        # Connect personas to the primary business reference contexts
        if personas and profiles:
            edges.append(
                C4Edge(
                    id=f"e-{personas[0][0]}-{profiles[0].business_id}",
                    source=personas[0][0],
                    target=profiles[0].business_id,
                    label="Executes business workflows in",
                    data=EdgeData(technology="HTTPS / Web UI"),
                )
            )
            if len(profiles) > 1:
                edges.append(
                    C4Edge(
                        id=f"e-{personas[0][0]}-{profiles[1].business_id}",
                        source=personas[0][0],
                        target=profiles[1].business_id,
                        label="Interacts with domain capabilities in",
                        data=EdgeData(technology="Interactive UI"),
                    )
                )
            if len(personas) > 1:
                target_prof = profiles[min(2, len(profiles) - 1)]
                edges.append(
                    C4Edge(
                        id=f"e-{personas[1][0]}-{target_prof.business_id}",
                        source=personas[1][0],
                        target=target_prof.business_id,
                        label="Governs & configures",
                        data=EdgeData(technology="RBAC / Admin"),
                    )
                )

        # Connect business reference contexts to show how business workflows flow across domains
        for i in range(len(profiles) - 1):
            edges.append(
                C4Edge(
                    id=f"e-biz-{profiles[i].business_id}-{profiles[i + 1].business_id}",
                    source=profiles[i].business_id,
                    target=profiles[i + 1].business_id,
                    label="Coordinates business context with",
                    data=EdgeData(technology="Domain Workflow"),
                )
            )

        # 3. External Business & Platform Systems on the right
        externals = _discover_external_systems(inventory)
        ext_x = 310 + b_width + 65
        for idx, (ext_id, ext_name, ext_tech, ext_desc) in enumerate(externals):
            nodes.append(
                C4Node(
                    id=ext_id,
                    position=Position(x=ext_x, y=60 + idx * 185),
                    data=NodeData(
                        kind="systemExternal",
                        name=ext_name,
                        technology=ext_tech,
                        description=ext_desc,
                        parentNodeId=None,
                    ),
                )
            )
            src_prof = profiles[idx % len(profiles)]
            edges.append(
                C4Edge(
                    id=f"e-{src_prof.business_id}-{ext_id}",
                    source=src_prof.business_id,
                    target=ext_id,
                    label="Integrates with",
                    data=EdgeData(technology=ext_tech),
                )
            )

        return LLMExtraction(boundaries=boundaries, nodes=nodes, edges=edges)


class ContainerSubagent(BaseLayerSubagent):
    agent_id = "subagent-container"
    role = "Container Layer Specialist Subagent"
    layer: Layer = "container"

    def extract_deterministic(
        self, inventory: RepoInventory, parent_nodes: list[C4Node]
    ) -> LLMExtraction:
        profiles = _discover_container_profiles(inventory)
        system_parents = [p for p in parent_nodes if p.data.kind == "system"]
        parent_by_scope = {
            (p.data.sourceScope or ""): p for p in system_parents if p.data.sourceScope
        }
        fallback_sys = system_parents[0] if system_parents else None

        # Carry forward EVERY upper-layer Business Context system as an enlarged,
        # transparent-bordered boundary that zooms in to reveal its Container(s) inside!
        boundaries: list[Boundary] = []
        nodes: list[C4Node] = []
        edges: list[C4Edge] = []

        grid_cols = min(3, max(1, len(profiles)))
        box_w = 305
        box_h = 280
        gap_x = 45
        gap_y = 48
        start_x = 290
        start_y = 40

        for idx, prof in enumerate(profiles):
            col = idx % grid_cols
            row = idx // grid_cols
            bx = start_x + col * (box_w + gap_x)
            by = start_y + row * (box_h + gap_y)

            matched_sys = (
                parent_by_scope.get(prof.scope_key)
                or (system_parents[idx % len(system_parents)] if system_parents else fallback_sys)
            )
            sys_id = matched_sys.id if matched_sys else prof.business_id
            sys_name = matched_sys.data.name if matched_sys else prof.business_name
            sys_desc = matched_sys.data.description if matched_sys else prof.business_desc

            boundary_id = f"boundary-ctx-{_slug(sys_id)}-{idx}"
            boundaries.append(
                Boundary(
                    id=boundary_id,
                    label=sys_name,
                    subtitle=f"Upper Layer: Business Context (Zoomed In) · {', '.join(prof.folder_names)}/",
                    description=sys_desc,
                    upperLayer="context",
                    sourceNodeId=sys_id,
                    position=Position(x=bx, y=by),
                    size=Size(width=box_w, height=box_h),
                )
            )

            nodes.append(
                C4Node(
                    id=prof.container_id,
                    position=Position(x=42, y=102),
                    parentId=boundary_id,
                    extent="parent",
                    data=NodeData(
                        kind=prof.container_kind,
                        name=prof.container_name,
                        technology=prof.container_tech,
                        description=prof.container_desc,
                        parentNodeId=sys_id,
                        sourceScope=prof.scope_key,
                    ),
                )
            )

        # Carry forward Personas (left) and External Systems (right) from Context layer
        actor_parents = [p for p in parent_nodes if p.data.kind == "person"]
        ext_parents = [p for p in parent_nodes if p.data.kind == "systemExternal"]

        for idx, actor in enumerate(actor_parents[:2]):
            actor_node_id = f"cont-{actor.id}"
            nodes.append(
                C4Node(
                    id=actor_node_id,
                    position=Position(x=20, y=80 + idx * 220),
                    data=NodeData(
                        kind="person",
                        name=actor.data.name,
                        technology=actor.data.technology,
                        description=actor.data.description,
                        parentNodeId=actor.id,
                    ),
                )
            )
            if profiles:
                edges.append(
                    C4Edge(
                        id=f"e-{actor_node_id}-{profiles[0].container_id}",
                        source=actor_node_id,
                        target=profiles[0].container_id,
                        label="Uses application routes & views",
                        data=EdgeData(technology="HTTPS"),
                    )
                )
                if len(profiles) > 1 and idx == 0:
                    edges.append(
                        C4Edge(
                            id=f"e-{actor_node_id}-{profiles[1].container_id}",
                            source=actor_node_id,
                            target=profiles[1].container_id,
                            label="Interacts with UI components in",
                            data=EdgeData(technology="Browser DOM / Events"),
                        )
                    )

        # Connect containers in architectural flow order
        for i in range(len(profiles) - 1):
            src_id = profiles[i].container_id
            tgt_id = profiles[i + 1].container_id
            edges.append(
                C4Edge(
                    id=f"e-{src_id}-{tgt_id}",
                    source=src_id,
                    target=tgt_id,
                    label="Invokes / delegates to",
                    data=EdgeData(technology="TypeScript / Internal API"),
                )
            )

        right_edge_x = start_x + grid_cols * (box_w + gap_x) + 25
        for idx, ext in enumerate(ext_parents[:3]):
            ext_node_id = f"cont-{ext.id}"
            nodes.append(
                C4Node(
                    id=ext_node_id,
                    position=Position(x=right_edge_x, y=60 + idx * 195),
                    data=NodeData(
                        kind="systemExternal",
                        name=ext.data.name,
                        technology=ext.data.technology,
                        description=ext.data.description,
                        parentNodeId=ext.id,
                    ),
                )
            )
            src_prof = profiles[min(idx + 1, len(profiles) - 1)] if len(profiles) > 1 else profiles[0]
            edges.append(
                C4Edge(
                    id=f"e-{src_prof.container_id}-{ext_node_id}",
                    source=src_prof.container_id,
                    target=ext_node_id,
                    label="Reads/writes & integrates with",
                    data=EdgeData(technology=ext.data.technology or "HTTPS / SDK"),
                )
            )

        return LLMExtraction(boundaries=boundaries, nodes=nodes, edges=edges)


def _extract_components_for_container(
    inventory: RepoInventory,
    container_node: C4Node,
    fallback_files: list[Path],
    max_components: int = 4,
) -> list[dict]:
    """Discover 2-4 cohesive internal components inside a specific Container's scope."""
    scope_raw = container_node.data.sourceScope or ""
    scope_folders = [s.strip() for s in scope_raw.split(",") if s.strip()]

    if not scope_folders:
        # Infer from container id or name
        inferred = container_node.id.removeprefix("cont-")
        scope_folders = [inferred]

    scoped_files: list[Path] = []
    for f in inventory.files:
        rel = f.relative_to(inventory.root)
        top = rel.parts[0] if len(rel.parts) > 1 else "root"
        if top in scope_folders or (
            "root" in scope_folders and len(rel.parts) == 1
        ):
            scoped_files.append(f)

    if not scoped_files:
        scoped_files = fallback_files

    # Filter out pure test/config files when possible
    meaningful_files = [
        f
        for f in scoped_files
        if not f.name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
        and f.stem not in {"__init__", "vite.config", "svelte.config", "jest.config", "vitest.config"}
    ]
    if not meaningful_files:
        meaningful_files = scoped_files

    # Group files inside this container into sub-modules / feature clusters
    clusters: dict[str, list[Path]] = {}
    for f in meaningful_files:
        rel = f.relative_to(inventory.root)
        parts = rel.parts
        if len(parts) >= 3:
            # e.g., app/(app)/pods/page.tsx -> "(app)/pods" or lib/assistant/... -> "assistant"
            if parts[1].startswith("(") and len(parts) >= 4:
                group_key = f"{parts[1]}/{parts[2]}"
            else:
                group_key = parts[1]
        elif len(parts) == 2:
            stem = f.stem
            # Group hooks like use-assistant-chat.ts -> "assistant-hooks", use-hiring-queries.ts -> "hiring-hooks"
            if stem.startswith("use-"):
                tokens = stem.removeprefix("use-").split("-")
                domain_tok = tokens[0] if tokens else "state"
                if domain_tok in {"assistant", "workflow", "consume"}:
                    group_key = "assistant-workflow-hooks"
                elif domain_tok in {"pod", "hiring", "portfolio", "seat", "product", "chapter", "manager", "job"}:
                    group_key = "pod-hiring-portfolio-hooks"
                else:
                    group_key = "lookup-ui-state-hooks"
            else:
                group_key = stem
        else:
            group_key = f.stem

        if group_key in {"__tests__", "fixtures", "mocks"}:
            continue
        clusters.setdefault(group_key, []).append(f)

    sorted_clusters = sorted(
        clusters.items(),
        key=lambda item: (
            sum(1 for p in item[1] if p.suffix in CODE_EXTS),
            len(item[1]),
        ),
        reverse=True,
    )

    tech_map = {
        ".py": "Python Module",
        ".svelte": "Svelte 5 Component",
        ".tsx": "React 19 / TSX Component",
        ".jsx": "React Component",
        ".ts": "TypeScript Module",
        ".js": "JavaScript Module",
        ".sql": "PostgreSQL Migration / RLS",
        ".md": "Skill / Architecture Spec",
        ".json": "JSON Schema / Data",
    }

    components_out: list[dict] = []
    for cluster_key, cluster_files in sorted_clusters[:max_components]:
        rep_file = sorted(
            cluster_files,
            key=lambda p: (p.suffix in CODE_EXTS, len(p.stem)),
            reverse=True,
        )[0]
        rel_rep = rep_file.relative_to(inventory.root)
        top_dir = rel_rep.parts[0] if len(rel_rep.parts) > 1 else "root"

        comp_id = f"comp-{_slug(container_node.id)}-{_slug(cluster_key)}"
        readable_cluster = _humanize_token(cluster_key.replace("/", " "))
        container_short = _humanize_token(top_dir)

        if len(cluster_files) > 1:
            comp_name = f"{readable_cluster} ({container_short})"
            sample_stems = ", ".join(
                dict.fromkeys(p.stem for p in cluster_files[:4] if p.stem not in {"index", "page", "layout", "route"})
            )
            tech = f"{tech_map.get(rep_file.suffix, 'Module')} · {len(cluster_files)} files"
            file_hint = _summarize_file(rep_file, rel_rep)
            desc = (
                f"Component module in `{top_dir}/{cluster_key}` ({len(cluster_files)} files"
                + (f": {sample_stems}" if sample_stems else "")
                + f"). {file_hint}"
            )[:210]
            comp_scope = f"{top_dir}/{cluster_key}"
        else:
            comp_name = f"{_humanize_token(rep_file.stem)} ({container_short})"
            tech = tech_map.get(rep_file.suffix, f"{rep_file.suffix.lstrip('.')} component")
            desc = _summarize_file(rep_file, rel_rep)
            comp_scope = str(rel_rep)

        components_out.append(
            {
                "id": comp_id,
                "name": comp_name,
                "technology": tech,
                "description": desc,
                "parentNodeId": container_node.id,
                "sourceScope": comp_scope,
                "files": cluster_files,
            }
        )

    return components_out


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

        # Carry forward EVERY upper-layer Container into the Component layer as an
        # enlarged, transparent-bordered boundary that zooms in and opens up to
        # explain the internal components inside that container!
        boundaries: list[Boundary] = []
        nodes: list[C4Node] = []
        edges: list[C4Edge] = []

        # Layout container boundaries in a 2-column grid of enlarged transparent boxes
        container_cols = 2 if len(in_scope_containers) > 1 else 1
        comp_cols = 2
        node_step_x = 258
        node_step_y = 178
        pad_x = 36
        pad_top = 102  # Room at the top of the transparent border for the zoomed-in container header
        pad_bottom = 34

        # Precompute components per container so we can size each enlarged boundary accurately
        container_groups: list[tuple[C4Node, list[dict], int, int]] = []
        for cont in in_scope_containers:
            comps = _extract_components_for_container(
                inventory, cont, inventory.files[:4], max_components=4
            )
            c_cols = min(comp_cols, max(1, len(comps)))
            c_rows = (len(comps) + c_cols - 1) // c_cols
            b_w = max(560, c_cols * node_step_x + pad_x * 2)
            b_h = max(270, c_rows * node_step_y + pad_top + pad_bottom)
            container_groups.append((cont, comps, b_w, b_h))

        col_width = max((g[2] for g in container_groups), default=580) + 55
        row_heights: dict[int, int] = {}
        for idx, (_, _, _, b_h) in enumerate(container_groups):
            r = idx // container_cols
            row_heights[r] = max(row_heights.get(r, 0), b_h)

        first_comp_by_container: list[str] = []

        for idx, (cont, comps, b_w, b_h) in enumerate(container_groups):
            b_col = idx % container_cols
            b_row = idx // container_cols
            bx = 40 + b_col * col_width
            by = 40 + sum(row_heights[r] + 55 for r in range(b_row))

            boundary_id = f"boundary-{cont.id}"
            boundaries.append(
                Boundary(
                    id=boundary_id,
                    label=cont.data.name,
                    subtitle=f"Upper Layer: Container (Zoomed In) · {cont.data.technology or 'Container'}",
                    description=cont.data.description,
                    upperLayer="container",
                    sourceNodeId=cont.id,
                    position=Position(x=bx, y=by),
                    size=Size(width=b_w, height=b_h),
                )
            )

            c_cols = min(comp_cols, max(1, len(comps)))
            comp_ids_in_container: list[str] = []
            for c_idx, comp in enumerate(comps):
                ccol = c_idx % c_cols
                crow = c_idx // c_cols
                nodes.append(
                    C4Node(
                        id=comp["id"],
                        position=Position(
                            x=pad_x + ccol * node_step_x,
                            y=pad_top + crow * node_step_y,
                        ),
                        parentId=boundary_id,
                        extent="parent",
                        data=NodeData(
                            kind="component",
                            name=comp["name"],
                            technology=comp["technology"],
                            description=comp["description"],
                            parentNodeId=cont.id,
                            sourceScope=comp["sourceScope"],
                        ),
                    )
                )
                comp_ids_in_container.append(comp["id"])

            if comp_ids_in_container:
                first_comp_by_container.append(comp_ids_in_container[0])

            # Connect components inside the same zoomed-in container
            for i in range(len(comp_ids_in_container) - 1):
                edges.append(
                    C4Edge(
                        id=f"e-intra-{comp_ids_in_container[i]}-{comp_ids_in_container[i + 1]}",
                        source=comp_ids_in_container[i],
                        target=comp_ids_in_container[i + 1],
                        label="Delegates within container to",
                        data=EdgeData(technology="Internal Module Call"),
                    )
                )

        # Connect primary components across zoomed-in containers to show cross-container component flow
        for i in range(len(first_comp_by_container) - 1):
            edges.append(
                C4Edge(
                    id=f"e-cross-{first_comp_by_container[i]}-{first_comp_by_container[i + 1]}",
                    source=first_comp_by_container[i],
                    target=first_comp_by_container[i + 1],
                    label="Invokes cross-container component",
                    data=EdgeData(technology="Typed Import / API"),
                )
            )

        return LLMExtraction(boundaries=boundaries, nodes=nodes, edges=edges)


def _extract_symbols_from_files(
    files: list[Path],
    inventory: RepoInventory,
    parent_comp: C4Node,
    max_symbols: int = 2,
) -> list[dict]:
    """Extract 1-3 concrete classes, interfaces, hooks, functions, or SQL tables for one Component."""
    symbols: list[dict] = []
    seen_ids: set[str] = set()

    def _add_symbol(sym_id: str, name: str, kind: Kind, tech: str, desc: str) -> None:
        if sym_id in seen_ids or len(symbols) >= max_symbols:
            return
        seen_ids.add(sym_id)
        symbols.append(
            {
                "id": sym_id,
                "name": name,
                "kind": kind,
                "technology": tech,
                "description": desc[:150],
                "parentNodeId": parent_comp.id,
            }
        )

    for f in files:
        if len(symbols) >= max_symbols:
            break
        if f.suffix == ".py":
            try:
                tree = ast.parse(f.read_text(errors="ignore"))
            except Exception:
                continue
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    bases = [ast.unparse(b) for b in node.bases] if node.bases else []
                    kind: Kind = "codeEnum" if any("Enum" in b for b in bases) else "codeClass"
                    doc = (ast.get_docstring(node) or f"Class `{node.name}` in `{f.name}`.").splitlines()[0]
                    _add_symbol(
                        f"code-{_slug(parent_comp.id)}-{_slug(node.name)}",
                        node.name,
                        kind,
                        f"Python class ({f.name})",
                        doc,
                    )
                elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    doc = (ast.get_docstring(node) or f"Function `{node.name}()` in `{f.name}`.").splitlines()[0]
                    _add_symbol(
                        f"code-{_slug(parent_comp.id)}-{_slug(node.name)}",
                        f"{node.name}()",
                        "codeInterface",
                        f"Python function ({f.name})",
                        doc,
                    )
        elif f.suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".svelte"}:
            text = f.read_text(errors="ignore")
            for match in re.finditer(
                r"export\s+(?:default\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)", text
            ):
                fn_name = match.group(1)
                is_component = f.suffix in {".tsx", ".jsx"} and fn_name[0].isupper()
                _add_symbol(
                    f"code-{_slug(parent_comp.id)}-{_slug(fn_name)}",
                    f"<{fn_name} />" if is_component else f"{fn_name}()",
                    "codeClass" if is_component else "codeInterface",
                    f"{'React Component' if is_component else 'Exported Function'} ({f.name})",
                    f"{'Renders UI component' if is_component else 'Executes module function'} `{fn_name}` in `{f.name}`.",
                )
            for match in re.finditer(r"export\s+(?:interface|type)\s+([A-Za-z0-9_]+)", text):
                type_name = match.group(1)
                _add_symbol(
                    f"code-{_slug(parent_comp.id)}-{_slug(type_name)}",
                    type_name,
                    "codeInterface",
                    f"TypeScript Contract ({f.name})",
                    f"Type contract `{type_name}` defined in `{f.name}`.",
                )
            for match in re.finditer(r"export\s+class\s+([A-Za-z0-9_]+)", text):
                cls_name = match.group(1)
                _add_symbol(
                    f"code-{_slug(parent_comp.id)}-{_slug(cls_name)}",
                    cls_name,
                    "codeClass",
                    f"Class ({f.name})",
                    f"Exported class `{cls_name}` in `{f.name}`.",
                )
            for match in re.finditer(r"export\s+const\s+([A-Za-z0-9_]+)", text):
                const_name = match.group(1)
                is_hook = const_name.startswith("use") and len(const_name) > 3
                _add_symbol(
                    f"code-{_slug(parent_comp.id)}-{_slug(const_name)}",
                    f"{const_name}()" if is_hook else const_name,
                    "codeInterface" if is_hook else "codeEnum",
                    f"{'React Hook' if is_hook else 'Exported Symbol'} ({f.name})",
                    f"Exported symbol `{const_name}` in `{f.name}`.",
                )
            if f.suffix == ".svelte":
                _add_symbol(
                    f"code-{_slug(parent_comp.id)}-svelte-{_slug(f.stem)}",
                    f"<{f.stem} />",
                    "codeClass",
                    f"Svelte 5 Component ({f.name})",
                    _summarize_file(f, f.relative_to(inventory.root)),
                )
        elif f.suffix == ".sql":
            text = f.read_text(errors="ignore")
            for match in re.finditer(
                r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:POLICY|FUNCTION|TABLE|TRIGGER)\s+\"?([A-Za-z0-9_]+)\"?",
                text,
                re.IGNORECASE,
            ):
                sql_name = match.group(1)
                _add_symbol(
                    f"code-{_slug(parent_comp.id)}-sql-{_slug(sql_name)}",
                    sql_name,
                    "codeEnum",
                    f"SQL Policy / Trigger ({f.name})",
                    f"Database DDL/RLS definition `{sql_name}` in `{f.name}`.",
                )

    if not symbols and files:
        rep = files[0]
        rel = rep.relative_to(inventory.root)
        _add_symbol(
            f"code-{_slug(parent_comp.id)}-mod-{_slug(rep.stem)}",
            rep.name,
            "codeClass",
            f"{rep.suffix.lstrip('.') or 'source'} module",
            _summarize_file(rep, rel),
        )

    return symbols


class CodeSubagent(BaseLayerSubagent):
    agent_id = "subagent-code"
    role = "Code Layer Specialist Subagent"
    layer: Layer = "code"

    def extract_deterministic(
        self, inventory: RepoInventory, parent_nodes: list[C4Node]
    ) -> LLMExtraction:
        component_parents = [p for p in parent_nodes if p.data.kind == "component"] or parent_nodes

        # Select components across ALL parent containers so every container's components
        # are carried forward with enlarged transparent borders in the Code layer!
        by_container: dict[str, list[C4Node]] = {}
        for comp in component_parents:
            cid = comp.data.parentNodeId or "default"
            by_container.setdefault(cid, []).append(comp)

        selected_components: list[C4Node] = []
        round_idx = 0
        while len(selected_components) < min(8, len(component_parents)):
            added_any = False
            for cid, comp_list in by_container.items():
                if round_idx < len(comp_list) and len(selected_components) < 8:
                    selected_components.append(comp_list[round_idx])
                    added_any = True
            if not added_any:
                break
            round_idx += 1

        boundaries: list[Boundary] = []
        nodes: list[C4Node] = []
        edges: list[C4Edge] = []

        grid_cols = 2 if len(selected_components) > 1 else 1
        node_step_x = 255
        pad_x = 34
        pad_top = 102
        pad_bottom = 32

        comp_symbol_groups: list[tuple[C4Node, list[dict], int, int]] = []
        for comp in selected_components:
            scope = comp.data.sourceScope or ""
            matched_files = [
                f
                for f in inventory.files
                if scope
                and str(f.relative_to(inventory.root)).startswith(scope)
                and f.suffix in CODE_EXTS
            ]
            if not matched_files and scope:
                top_scope = scope.split("/")[0]
                matched_files = [
                    f
                    for f in inventory.files
                    if str(f.relative_to(inventory.root)).startswith(top_scope + "/")
                    and f.suffix in CODE_EXTS
                ]
            if not matched_files:
                matched_files = [
                    f for f in inventory.files if f.stem.lower() in comp.data.name.lower()
                ] or [f for f in inventory.files if f.suffix in CODE_EXTS][:3]

            syms = _extract_symbols_from_files(matched_files, inventory, comp, max_symbols=2)
            s_cols = min(2, max(1, len(syms)))
            s_rows = (len(syms) + s_cols - 1) // s_cols
            b_w = max(320, s_cols * node_step_x + pad_x * 2)
            b_h = max(255, s_rows * 175 + pad_top + pad_bottom)
            comp_symbol_groups.append((comp, syms, b_w, b_h))

        col_width = max((g[2] for g in comp_symbol_groups), default=560) + 50
        row_heights: dict[int, int] = {}
        for idx, (_, _, _, b_h) in enumerate(comp_symbol_groups):
            r = idx // grid_cols
            row_heights[r] = max(row_heights.get(r, 0), b_h)

        first_sym_per_comp: list[str] = []

        for idx, (comp, syms, b_w, b_h) in enumerate(comp_symbol_groups):
            b_col = idx % grid_cols
            b_row = idx // grid_cols
            bx = 40 + b_col * col_width
            by = 40 + sum(row_heights[r] + 50 for r in range(b_row))

            boundary_id = f"boundary-code-{comp.id}"
            boundaries.append(
                Boundary(
                    id=boundary_id,
                    label=comp.data.name,
                    subtitle=f"Upper Layer: Component (Zoomed In) · {comp.data.technology or 'Component'}",
                    description=comp.data.description,
                    upperLayer="component",
                    sourceNodeId=comp.id,
                    position=Position(x=bx, y=by),
                    size=Size(width=b_w, height=b_h),
                )
            )

            sym_ids: list[str] = []
            for s_idx, sym in enumerate(syms):
                scol = s_idx % 2
                srow = s_idx // 2
                nodes.append(
                    C4Node(
                        id=sym["id"],
                        position=Position(
                            x=pad_x + scol * node_step_x,
                            y=pad_top + srow * 175,
                        ),
                        parentId=boundary_id,
                        extent="parent",
                        data=NodeData(
                            kind=sym["kind"],
                            name=sym["name"],
                            technology=sym["technology"],
                            description=sym["description"],
                            parentNodeId=comp.id,
                        ),
                    )
                )
                sym_ids.append(sym["id"])

            if sym_ids:
                first_sym_per_comp.append(sym_ids[0])

            for i in range(len(sym_ids) - 1):
                edges.append(
                    C4Edge(
                        id=f"e-code-intra-{sym_ids[i]}-{sym_ids[i + 1]}",
                        source=sym_ids[i],
                        target=sym_ids[i + 1],
                        label="invokes / types",
                        data=EdgeData(technology=None),
                    )
                )

        for i in range(len(first_sym_per_comp) - 1):
            edges.append(
                C4Edge(
                    id=f"e-code-cross-{first_sym_per_comp[i]}-{first_sym_per_comp[i + 1]}",
                    source=first_sym_per_comp[i],
                    target=first_sym_per_comp[i + 1],
                    label="imports / calls",
                    data=EdgeData(technology=None),
                )
            )

        return LLMExtraction(boundaries=boundaries, nodes=nodes, edges=edges)


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

    for line in content.splitlines()[:15]:
        stripped = line.strip().lstrip("/#*<!- ").rstrip("->")
        if (
            len(stripped) > 18
            and not stripped.startswith(("import ", "from ", "<script", "{", "'use ", '"use ', "export "))
        ):
            return f"{stripped[:110]} (`{rel_path}`)"

    return f"Implements `{file_path.stem}` responsibilities in `{rel_path}`."


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
        self.adapter: LLMHubAdapter = get_adapter(self.agent_id)
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
            # Specialists always use their medium-tier adapter model unless overridden.
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

        hierarchy_note = ""
        if use_llm:
            try:
                hierarchy_note = self._refine_hierarchy_summary(
                    inventory=inventory,
                    total_nodes=total_nodes,
                    total_edges=total_edges,
                    model=model or self.adapter.model,
                )
            except Exception as exc:
                logger.debug("[%s] hierarchy refine skipped: %s", self.agent_id, exc)

        supervisor_report = AgentReport(
            agent_id=self.agent_id,
            role=self.role,
            layer=None,
            status="completed",
            summary=(
                f"Coordinated 4 specialist subagents (Context -> Container -> Component -> Code) "
                f"via LLMHub {self.adapter.tier}/{self.adapter.model} and verified parent-child "
                f"hierarchy across {total_nodes} nodes and {total_edges} edges."
                + (f" {hierarchy_note}" if hierarchy_note else "")
            ),
            produced_nodes=total_nodes,
            produced_edges=total_edges,
        )
        return layers_out, hierarchy, [supervisor_report, *reports]

    def _refine_hierarchy_summary(
        self,
        inventory: RepoInventory,
        total_nodes: int,
        total_edges: int,
        model: str,
    ) -> str:
        """Use the powerful Supervisor adapter to produce a short hierarchy QA note."""
        prompt = (
            f"Repo: {inventory.repo_name}. Layers extracted with {total_nodes} nodes and "
            f"{total_edges} edges across Context→Container→Component→Code. "
            "Reply with ONE short sentence confirming hierarchical parent-child consistency "
            "expectations for C4 (no markdown)."
        )
        return self.adapter.chat_text(
            "You are the C4 hierarchy supervisor. Be concise.",
            prompt,
            model=model,
            temperature=0.1,
        ).strip()

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
        self.adapter: LLMHubAdapter = get_adapter(self.agent_id)
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

            llm_ready = bool(use_llm and is_hub_reachable())
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
                    f"via LLMHub {self.adapter.tier}/{self.adapter.model} and delegated "
                    f"hierarchical C4 generation to Supervisor"
                    f"{' (LLMHub online)' if llm_ready else ' (deterministic fallback)'}."
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
