"""Tests for parallel Component/Code fan-out helpers and extraction."""

from __future__ import annotations

import os
import time
from pathlib import Path

from app.agents import (
    ComponentSubagent,
    ManagerAgent,
    RepoInventory,
    _merge_extractions,
    _scoped_inventory,
)
from app.folder_classifier import classify_project
from app.parallel_extract import map_parallel, max_workers
from app.schemas import (
    C4Node,
    LLMExtraction,
    NodeData,
    Position,
)


def test_map_parallel_preserves_order_and_overlaps() -> None:
    started: list[float] = []

    def _work(n: int) -> int:
        started.append(time.perf_counter())
        time.sleep(0.05)
        return n * 2

    os.environ["C4_PARALLEL_WORKERS"] = "4"
    try:
        out = map_parallel(_work, [1, 2, 3, 4], label="test")
    finally:
        os.environ.pop("C4_PARALLEL_WORKERS", None)

    assert out == [2, 4, 6, 8]
    # Overlap: last start should happen before first could finish serially.
    assert max(started) - min(started) < 0.15


def test_max_workers_respects_env() -> None:
    os.environ["C4_PARALLEL_WORKERS"] = "1"
    try:
        assert max_workers(10) == 1
    finally:
        os.environ.pop("C4_PARALLEL_WORKERS", None)


def test_scoped_inventory_filters_files(tmp_path: Path) -> None:
    (tmp_path / "auth").mkdir()
    (tmp_path / "billing").mkdir()
    auth = tmp_path / "auth" / "service.py"
    billing = tmp_path / "billing" / "service.py"
    auth.write_text("class Auth: pass\n")
    billing.write_text("class Billing: pass\n")

    inventory = RepoInventory(
        root=tmp_path,
        source_label=str(tmp_path),
        source_type="local",
        repo_name="demo",
        files=[auth, billing],
        repo_context="full",
        project_plan=None,
    )
    scoped = _scoped_inventory(inventory, "auth")
    assert scoped.files == [auth]
    assert "auth/service.py" in scoped.repo_context
    assert "billing" not in scoped.repo_context


def test_merge_extractions_dedupes_nodes() -> None:
    node = C4Node(
        id="n1",
        position=Position(x=0, y=0),
        data=NodeData(kind="component", name="A", description="d"),
    )
    a = LLMExtraction(nodes=[node], edges=[])
    b = LLMExtraction(nodes=[node], edges=[])
    merged = _merge_extractions([a, b])
    assert len(merged.nodes) == 1


def test_component_and_code_parallel_on_monorepo(tmp_path: Path) -> None:
    for name in ("frontend", "backend"):
        d = tmp_path / name
        d.mkdir()
        (d / "Dockerfile").write_text("FROM scratch\n")
    (tmp_path / "frontend" / "package.json").write_text(
        '{"name":"web","scripts":{"dev":"vite"},"main":"i.js"}'
    )
    (tmp_path / "frontend" / "src").mkdir()
    (tmp_path / "frontend" / "src" / "App.svelte").write_text("<script>export let x;</script>\n")
    (tmp_path / "backend" / "app").mkdir()
    (tmp_path / "backend" / "app" / "main.py").write_text(
        '"""API."""\nclass AppService:\n    pass\n\ndef run():\n    pass\n'
    )
    (tmp_path / "backend" / "app" / "auth.py").write_text("class AuthService: pass\n")
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  frontend:\n    build: ./frontend\n  backend:\n    build: ./backend\n"
    )

    result = ManagerAgent().analyze(str(tmp_path), source_type="local", use_llm=False)
    assert result.project_plan is not None
    assert "parallel Component" in result.agents[1].summary or "parallel" in result.agents[1].summary.lower()

    component_layer = result.layers["component"]
    code_layer = result.layers["code"]
    assert len(component_layer.nodes) >= 1
    assert len(code_layer.nodes) >= 1

    # Hierarchy remains linked Context -> ... -> Code
    assert result.hierarchy
    assert any(n.children for n in result.hierarchy)


def test_component_subagent_discovers_in_parallel(tmp_path: Path) -> None:
    plan = None
    files: list[Path] = []
    for name in ("auth", "billing", "notify"):
        folder = tmp_path / name
        folder.mkdir()
        f = folder / "service.py"
        f.write_text(f"class {name.title()}Service: pass\n")
        files.append(f)

    plan = classify_project(tmp_path, repo_name="feat")
    inventory = RepoInventory(
        root=tmp_path,
        source_label=str(tmp_path),
        source_type="local",
        repo_name="feat",
        files=files,
        repo_context="x",
        project_plan=plan,
    )
    # Synthetic single container owning all feature folders
    parent = C4Node(
        id="cont-app",
        position=Position(x=0, y=0),
        data=NodeData(
            kind="container",
            name="App",
            description="app",
            sourceScope="auth,billing,notify",
        ),
    )
    layer, report = ComponentSubagent().run(
        inventory, [parent], use_llm=False
    )
    assert layer.nodes
    assert report.produced_nodes == len(layer.nodes)
