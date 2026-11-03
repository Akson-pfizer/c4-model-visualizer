"""Classify project folders as container / component / shared / ignore.

Deterministic first (runtime, package, name, and import signals), with an
optional Manager-tier LLM tie-break when top scores are close. Used by
ManagerAgent to build a ProjectPlan before Supervisor extraction.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from app.repo_scanner import IGNORED_DIRS, INCLUDED_EXTENSIONS

logger = logging.getLogger(__name__)

FolderRole = Literal["container", "component", "shared", "ignore"]
ProjectStyle = Literal["feature_modules", "service_monorepo", "single_app", "mixed"]

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

MANIFEST_NAMES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "Pipfile",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Gemfile",
    "composer.json",
}

ENTRYPOINT_NAMES = {
    "main.py",
    "app.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "server.py",
    "index.ts",
    "index.tsx",
    "index.js",
    "index.jsx",
    "main.ts",
    "main.tsx",
    "main.js",
    "main.go",
    "main.rs",
    "App.svelte",
    "app.ts",
    "app.js",
}

IGNORE_NAMES = {
    ".github",
    ".gitlab",
    ".claude",
    ".cursor",
    ".vscode",
    ".idea",
    "e2e",
    "test",
    "tests",
    "__tests__",
    "docs",
    "documentation",
    "vendor",
    "claude_output",
    "coverage",
    "dist",
    "build",
    "scripts",
    "script",
    "examples",
    "example",
    "fixtures",
    "mocks",
    "assets",
    "static",
    "public",
    "images",
    "img",
    "tmp",
    "temp",
    "ops",
    "infra",
    "infrastructure",
    "deploy",
    "deployment",
    "ci",
    "helm",
    "k8s",
    "kubernetes",
    "terraform",
    "ansible",
}

CONTAINER_NAMES = {
    "frontend",
    "backend",
    "api",
    "server",
    "web",
    "client",
    "mobile",
    "android",
    "ios",
    "worker",
    "workers",
    "service",
    "services",
    "db",
    "database",
    "supabase",
    "postgres",
    "mysql",
    "mongo",
    "redis",
    "gateway",
    "proxy",
    "admin",
    "dashboard",
    "bff",
}

SHARED_NAMES = {
    "shared",
    "common",
    "lib",
    "libs",
    "library",
    "libraries",
    "packages",
    "pkg",
    "core",
    "utils",
    "util",
    "helpers",
    "types",
    "typing",
    "schemas",
    "contracts",
    "sdk",
    "platform",
}

AMBIGUOUS_MARGIN = 0.18
MIN_CODE_FILES_FOR_COMPONENT = 2


@dataclass
class FolderClassification:
    path: str
    name: str
    depth: int
    role: FolderRole
    confidence: float
    evidence: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    file_count: int = 0
    code_file_count: int = 0
    extensions: list[str] = field(default_factory=list)
    children: list[FolderClassification] = field(default_factory=list)
    refined_by_llm: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "depth": self.depth,
            "role": self.role,
            "confidence": round(self.confidence, 3),
            "evidence": self.evidence,
            "scores": {k: round(v, 3) for k, v in self.scores.items()},
            "file_count": self.file_count,
            "code_file_count": self.code_file_count,
            "extensions": self.extensions,
            "children": [c.to_dict() for c in self.children],
            "refined_by_llm": self.refined_by_llm,
        }


@dataclass
class ProjectPlan:
    root: str
    repo_name: str
    style: ProjectStyle
    folders: list[FolderClassification]
    summary: str

    @property
    def containers(self) -> list[FolderClassification]:
        return [f for f in self.folders if f.role == "container"]

    @property
    def components(self) -> list[FolderClassification]:
        out: list[FolderClassification] = []
        for f in self.folders:
            if f.role == "component":
                out.append(f)
            for child in f.children:
                if child.role == "component":
                    out.append(child)
        return out

    @property
    def shared(self) -> list[FolderClassification]:
        out: list[FolderClassification] = []
        for f in self.folders:
            if f.role == "shared":
                out.append(f)
            for child in f.children:
                if child.role == "shared":
                    out.append(child)
        return out

    def scopes_for_role(self, role: FolderRole) -> list[str]:
        return [f.path for f in self.folders if f.role == role] + [
            c.path
            for f in self.folders
            for c in f.children
            if c.role == role
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "repo_name": self.repo_name,
            "style": self.style,
            "summary": self.summary,
            "folders": [f.to_dict() for f in self.folders],
            "container_scopes": self.scopes_for_role("container"),
            "component_scopes": self.scopes_for_role("component"),
            "shared_scopes": self.scopes_for_role("shared"),
        }


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _parse_compose_services(root: Path) -> dict[str, set[str]]:
    """Map compose service name -> set of referenced folder names / contexts."""
    mapping: dict[str, set[str]] = {}
    for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        compose = root / name
        if not compose.exists():
            continue
        try:
            text = compose.read_text(errors="ignore")
        except OSError:
            continue
        # Lightweight YAML scrape — avoid hard dependency on PyYAML.
        current: str | None = None
        in_services = False
        for raw in text.splitlines():
            line = raw.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            if re.match(r"^services:\s*$", line):
                in_services = True
                current = None
                continue
            if in_services and re.match(r"^[A-Za-z0-9_.-]+:\s*$", line) and not line.startswith(" "):
                # Top-level key other than services ended the block.
                if line.strip().rstrip(":") != "services":
                    in_services = False
                    current = None
                continue
            if not in_services:
                continue
            svc = re.match(r"^  ([A-Za-z0-9_.-]+):\s*$", line)
            if svc:
                current = svc.group(1)
                mapping.setdefault(current, set())
                continue
            if current is None:
                continue
            for match in re.finditer(
                r"(?:context|dockerfile):\s*['\"]?\.?/?([A-Za-z0-9_.-]+)",
                line,
            ):
                mapping[current].add(match.group(1))
            for match in re.finditer(
                r"['\"]?\.?/?([A-Za-z0-9_.-]+)/Dockerfile",
                line,
            ):
                mapping[current].add(match.group(1))
            # volume mounts like ./backend:/app
            for match in re.finditer(
                r"['\"]?\./([A-Za-z0-9_.-]+)(?:/[^:'\"]*)?:",
                line,
            ):
                mapping[current].add(match.group(1))
            # service named same as folder is itself a hint
            mapping[current].add(current)
    return mapping


def _folders_referenced_by_compose(root: Path) -> set[str]:
    refs: set[str] = set()
    for folders in _parse_compose_services(root).values():
        refs.update(folders)
    return refs


def _has_start_script(folder: Path) -> bool:
    pkg = folder / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(errors="ignore"))
        except (OSError, json.JSONDecodeError):
            data = {}
        scripts = data.get("scripts") if isinstance(data, dict) else None
        if isinstance(scripts, dict):
            for key in ("start", "dev", "serve", "preview"):
                if key in scripts:
                    return True
        if isinstance(data, dict) and data.get("main"):
            return True

    pyproject = folder / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(errors="ignore").lower()
        except OSError:
            text = ""
        if "[project.scripts]" in text or "uvicorn" in text or "fastapi" in text:
            return True

    for marker in ("Procfile", "Dockerfile", "Containerfile"):
        if (folder / marker).exists():
            return True
    return False


def _has_entrypoint(folder: Path, files: list[Path]) -> bool:
    for f in files:
        if f.name in ENTRYPOINT_NAMES:
            return True
        # One level down common layouts: src/main.py, app/main.py
        try:
            rel = f.relative_to(folder)
        except ValueError:
            continue
        if len(rel.parts) == 2 and rel.parts[0] in {"src", "app", "cmd"} and rel.name in ENTRYPOINT_NAMES:
            return True
    return False


def _count_import_refs(
    folder_name: str,
    root: Path,
    all_files: list[Path],
) -> tuple[int, int]:
    """Approximate (dependents, dependencies): how often others import this folder,
    and how often this folder imports sibling top-level folders."""
    dependents = 0
    dependencies = 0
    # Patterns that suggest importing this package/folder
    patterns = [
        re.compile(rf"(?:from|import)\s+{re.escape(folder_name)}\b"),
        re.compile(rf"""['"](?:@?/|\.\./|\./)?{re.escape(folder_name)}/"""),
        re.compile(rf"""['"]{re.escape(folder_name)}['"]"""),
    ]
    sibling_names = {
        p.name
        for p in root.iterdir()
        if p.is_dir() and p.name not in IGNORED_DIRS and not p.name.startswith(".")
    } - {folder_name}

    folder_prefix = folder_name + "/"
    own_files: list[Path] = []
    other_files: list[Path] = []
    for f in all_files:
        rel = _rel(f, root)
        if rel == folder_name or rel.startswith(folder_prefix):
            own_files.append(f)
        else:
            other_files.append(f)

    sample_others = other_files[:400]
    for f in sample_others:
        try:
            text = f.read_text(errors="ignore")[:8000]
        except OSError:
            continue
        if any(p.search(text) for p in patterns):
            dependents += 1

    sample_own = own_files[:200]
    for f in sample_own:
        try:
            text = f.read_text(errors="ignore")[:8000]
        except OSError:
            continue
        for sib in sibling_names:
            if re.search(rf"(?:from|import)\s+{re.escape(sib)}\b", text) or f"{sib}/" in text:
                dependencies += 1
                break
    return dependents, dependencies


def _group_files_by_top(root: Path, files: list[Path]) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    for f in files:
        rel = f.relative_to(root)
        if not rel.parts:
            continue
        top = rel.parts[0] if len(rel.parts) > 1 else "__root__"
        groups.setdefault(top, []).append(f)
    return groups


def _score_folder(
    *,
    name: str,
    depth: int,
    files: list[Path],
    folder_path: Path,
    compose_refs: set[str],
    dependents: int,
    dependencies: int,
    parent_role: FolderRole | None = None,
) -> tuple[FolderRole, float, dict[str, float], list[str]]:
    scores: dict[str, float] = {
        "container": 0.0,
        "component": 0.0,
        "shared": 0.0,
        "ignore": 0.0,
    }
    evidence: list[str] = []

    lower = name.lower()
    code_files = [f for f in files if f.suffix in CODE_EXTS]
    code_count = len(code_files)
    exts = sorted({f.suffix for f in files if f.suffix})

    # --- ignore signals ---
    if lower in IGNORE_NAMES or lower.startswith("."):
        scores["ignore"] += 3.0
        evidence.append(f"name '{name}' is tooling/noise")
    if code_count == 0 and not any(f.name in MANIFEST_NAMES for f in files):
        scores["ignore"] += 1.5
        evidence.append("no source/code files")
    if code_count < MIN_CODE_FILES_FOR_COMPONENT and scores["ignore"] < 2:
        scores["ignore"] += 0.4

    # --- container signals ---
    has_docker = (folder_path / "Dockerfile").exists() or (folder_path / "Containerfile").exists()
    if has_docker:
        scores["container"] += 2.5
        evidence.append("has Dockerfile/Containerfile")
    if name in compose_refs or lower in {r.lower() for r in compose_refs}:
        scores["container"] += 2.2
        evidence.append("referenced by docker-compose")
    has_manifest = any((folder_path / m).exists() for m in MANIFEST_NAMES) or any(
        f.name in MANIFEST_NAMES and f.parent == folder_path for f in files
    )
    if has_manifest:
        scores["container"] += 0.6
        evidence.append("has package/runtime manifest")
    if _has_start_script(folder_path):
        scores["container"] += 1.8
        evidence.append("has start/dev script or process marker")
    if _has_entrypoint(folder_path, files):
        scores["container"] += 1.2
        evidence.append("has runtime entrypoint")
    if lower in CONTAINER_NAMES:
        scores["container"] += 1.6
        evidence.append(f"name '{name}' suggests deployable/runtime")
    if any(f.suffix in {".sql"} for f in files) and lower in {
        "db",
        "database",
        "supabase",
        "migrations",
        "sql",
    }:
        scores["container"] += 1.0
        evidence.append("database/migration folder")

    # Nested folders need stronger runtime evidence to be containers.
    if depth >= 1:
        scores["container"] *= 0.55
        if parent_role == "container":
            scores["component"] += 0.8
            evidence.append("nested under a container → prefer component")

    # --- shared signals ---
    if lower in SHARED_NAMES:
        scores["shared"] += 2.4
        evidence.append(f"name '{name}' suggests shared library")
    if dependents >= 3 and not has_docker and not _has_start_script(folder_path):
        scores["shared"] += 1.5
        evidence.append(f"imported by {dependents} other files (library-like)")
    if dependents >= 2 and dependencies <= 1 and code_count >= 3:
        scores["shared"] += 0.7

    # --- component signals ---
    if code_count >= MIN_CODE_FILES_FOR_COMPONENT:
        scores["component"] += 1.0
        evidence.append(f"{code_count} code files")
    if (
        lower not in CONTAINER_NAMES
        and lower not in SHARED_NAMES
        and lower not in IGNORE_NAMES
        and code_count >= MIN_CODE_FILES_FOR_COMPONENT
    ):
        scores["component"] += 1.2
        evidence.append("domain-style name with source code")
    if not has_docker and not _has_start_script(folder_path) and code_count >= MIN_CODE_FILES_FOR_COMPONENT:
        scores["component"] += 0.9
        evidence.append("no own runtime → module/component")
    if dependencies >= 2 and dependents <= 1:
        scores["component"] += 0.5
        evidence.append("depends on siblings more than depended-upon")

    # Single-app feature folders under src/app often are components.
    if depth >= 1 and parent_role in (None, "container", "component"):
        if code_count >= 1 and scores["ignore"] < 2:
            scores["component"] += 0.6

    # Pick winner
    role = max(scores, key=lambda k: scores[k])  # type: ignore[arg-type]
    ranked = sorted(scores.values(), reverse=True)
    top, second = ranked[0], ranked[1] if len(ranked) > 1 else 0.0
    if top <= 0:
        role = "ignore"
        confidence = 0.4
        evidence.append("no positive signals → ignore")
    else:
        margin = top - second
        confidence = min(0.97, 0.45 + margin * 0.35 + (0.1 if top >= 2.5 else 0.0))
        if margin < AMBIGUOUS_MARGIN:
            confidence = min(confidence, 0.55)
            evidence.append(
                f"ambiguous scores (margin {margin:.2f}); needs review/LLM"
            )

    return role, confidence, scores, evidence  # type: ignore[return-value]


def _list_child_dirs(folder: Path) -> list[Path]:
    try:
        return sorted(
            p
            for p in folder.iterdir()
            if p.is_dir()
            and p.name not in IGNORED_DIRS
            and not p.name.startswith(".")
        )
    except OSError:
        return []


def _files_under(folder: Path, all_files: list[Path], root: Path) -> list[Path]:
    prefix = _rel(folder, root).rstrip("/") + "/"
    name = folder.name
    out: list[Path] = []
    for f in all_files:
        rel = _rel(f, root)
        if rel.startswith(prefix) or (folder == root / name and rel.startswith(name + "/")):
            out.append(f)
        elif folder.parent == root and rel.startswith(name + "/"):
            out.append(f)
    # Fallback walk if inventory missed nested files
    if not out:
        try:
            out = [
                p
                for p in folder.rglob("*")
                if p.is_file()
                and p.suffix in INCLUDED_EXTENSIONS
                and not any(part in IGNORED_DIRS for part in p.parts)
            ]
        except OSError:
            out = []
    return out


def classify_folder(
    folder: Path,
    *,
    root: Path,
    all_files: list[Path],
    depth: int = 0,
    compose_refs: set[str] | None = None,
    parent_role: FolderRole | None = None,
    classify_children: bool = True,
) -> FolderClassification:
    compose_refs = compose_refs if compose_refs is not None else _folders_referenced_by_compose(root)
    files = _files_under(folder, all_files, root)
    dependents, dependencies = _count_import_refs(folder.name, root, all_files)
    role, confidence, scores, evidence = _score_folder(
        name=folder.name,
        depth=depth,
        files=files,
        folder_path=folder,
        compose_refs=compose_refs,
        dependents=dependents,
        dependencies=dependencies,
        parent_role=parent_role,
    )
    if dependents or dependencies:
        evidence.append(f"import refs: dependents={dependents}, dependencies={dependencies}")

    children: list[FolderClassification] = []
    if classify_children and depth == 0 and role in {"container", "component", "shared"}:
        for child in _list_child_dirs(folder):
            # Skip deep noise; only first nesting level for major subfolders.
            child_files = _files_under(child, all_files, root)
            if not child_files and child.name.lower() in IGNORE_NAMES:
                continue
            child_cls = classify_folder(
                child,
                root=root,
                all_files=all_files,
                depth=1,
                compose_refs=compose_refs,
                parent_role=role,
                classify_children=False,
            )
            children.append(child_cls)

    return FolderClassification(
        path=_rel(folder, root),
        name=folder.name,
        depth=depth,
        role=role,
        confidence=confidence,
        evidence=evidence,
        scores=scores,
        file_count=len(files),
        code_file_count=sum(1 for f in files if f.suffix in CODE_EXTS),
        extensions=sorted({f.suffix for f in files if f.suffix}),
        children=children,
    )


def _infer_style(folders: list[FolderClassification]) -> ProjectStyle:
    roles = [f.role for f in folders if f.role != "ignore"]
    if not roles:
        return "single_app"
    n_cont = sum(1 for r in roles if r == "container")
    n_comp = sum(1 for r in roles if r == "component")
    n_shared = sum(1 for r in roles if r == "shared")
    if n_cont >= 2 and n_cont >= n_comp:
        return "service_monorepo"
    if n_comp >= 2 and n_cont <= 1:
        return "feature_modules"
    if n_cont <= 1 and n_comp <= 1 and n_shared <= 1:
        return "single_app"
    return "mixed"


def _summary_line(plan_style: ProjectStyle, folders: list[FolderClassification]) -> str:
    counts = {
        "container": 0,
        "component": 0,
        "shared": 0,
        "ignore": 0,
    }
    for f in folders:
        counts[f.role] = counts.get(f.role, 0) + 1
        for c in f.children:
            counts[c.role] = counts.get(c.role, 0) + 1
    return (
        f"Detected project style '{plan_style}' with "
        f"{counts['container']} container(s), {counts['component']} component(s), "
        f"{counts['shared']} shared, {counts['ignore']} ignored."
    )


def classify_project(
    root: Path,
    files: list[Path] | None = None,
    *,
    repo_name: str | None = None,
) -> ProjectPlan:
    """Classify first-class folders (and one level of subfolders) under root."""
    root = root.expanduser().resolve()
    if files is None:
        files = [
            p
            for p in sorted(root.rglob("*"))
            if p.is_file()
            and p.suffix in INCLUDED_EXTENSIONS
            and not any(part in IGNORED_DIRS for part in p.parts)
        ]

    compose_refs = _folders_referenced_by_compose(root)
    top_dirs = [
        p
        for p in sorted(root.iterdir())
        if p.is_dir() and p.name not in IGNORED_DIRS and not p.name.startswith(".")
    ]

    folders: list[FolderClassification] = []
    for d in top_dirs:
        folders.append(
            classify_folder(
                d,
                root=root,
                all_files=files,
                depth=0,
                compose_refs=compose_refs,
                classify_children=True,
            )
        )

    style = _infer_style(folders)
    name = repo_name or root.name
    return ProjectPlan(
        root=str(root),
        repo_name=name,
        style=style,
        folders=folders,
        summary=_summary_line(style, folders),
    )


def ambiguous_folders(
    plan: ProjectPlan,
    *,
    confidence_threshold: float = 0.58,
) -> list[FolderClassification]:
    found: list[FolderClassification] = []
    for f in plan.folders:
        if f.role != "ignore" and f.confidence < confidence_threshold:
            found.append(f)
        elif f.role == "ignore" and f.confidence < 0.5 and f.code_file_count >= MIN_CODE_FILES_FOR_COMPONENT:
            found.append(f)
        for c in f.children:
            if c.confidence < confidence_threshold and c.role != "ignore":
                found.append(c)
    return found


def refine_with_llm(
    plan: ProjectPlan,
    adapter: Any,
    *,
    model: str | None = None,
) -> ProjectPlan:
    """Ask Manager-tier adapter to relabel low-confidence folders. Best-effort."""
    ambiguous = ambiguous_folders(plan)
    if not ambiguous:
        return plan

    dossier = [
        {
            "path": f.path,
            "name": f.name,
            "depth": f.depth,
            "current_role": f.role,
            "confidence": f.confidence,
            "scores": f.scores,
            "evidence": f.evidence[:8],
            "code_file_count": f.code_file_count,
            "extensions": f.extensions,
        }
        for f in ambiguous
    ]
    system = (
        "You classify software repository folders for a C4 model. "
        "Roles: container (deployable/runtime), component (domain module), "
        "shared (library used by many), ignore (tooling/noise). "
        "Return JSON: {\"labels\": [{\"path\": \"...\", \"role\": \"container|component|shared|ignore\", "
        "\"reason\": \"...\"}]}."
    )
    user = (
        f"Repo: {plan.repo_name}. Inferred style so far: {plan.style}.\n"
        f"Re-label only these ambiguous folders:\n{json.dumps(dossier, indent=2)}"
    )
    try:
        raw = adapter.chat_json(system, user, model=model, temperature=0.1)
    except Exception as exc:  # noqa: BLE001
        logger.warning("folder classification LLM refine skipped: %s", exc)
        return plan

    labels = raw.get("labels") if isinstance(raw, dict) else None
    if not isinstance(labels, list):
        return plan

    by_path = {
        str(item.get("path")): str(item.get("role"))
        for item in labels
        if isinstance(item, dict) and item.get("path") and item.get("role") in {
            "container",
            "component",
            "shared",
            "ignore",
        }
    }
    if not by_path:
        return plan

    def _apply(node: FolderClassification) -> None:
        if node.path in by_path:
            new_role = by_path[node.path]  # type: ignore[assignment]
            if new_role != node.role:
                node.evidence.append(
                    f"LLM refine: {node.role} → {new_role}"
                )
            node.role = new_role  # type: ignore[assignment]
            node.confidence = max(node.confidence, 0.72)
            node.refined_by_llm = True
        for child in node.children:
            _apply(child)

    for folder in plan.folders:
        _apply(folder)

    plan.style = _infer_style(plan.folders)
    plan.summary = _summary_line(plan.style, plan.folders)
    return plan
