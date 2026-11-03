"""Unit tests for folder / subfolder role classification."""

from __future__ import annotations

import json
from pathlib import Path

from app.folder_classifier import (
    classify_project,
    refine_with_llm,
)


def _write(path: Path, content: str = "x = 1\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_service_monorepo_frontend_backend(tmp_path: Path) -> None:
    _write(
        tmp_path / "frontend" / "package.json",
        json.dumps({"name": "web", "scripts": {"dev": "vite"}, "main": "index.js"}),
    )
    _write(tmp_path / "frontend" / "src" / "main.ts", "console.log('hi')\n")
    _write(tmp_path / "frontend" / "Dockerfile", "FROM node:20\n")
    _write(tmp_path / "backend" / "pyproject.toml", "[project]\nname='api'\n")
    _write(tmp_path / "backend" / "app" / "main.py", "from fastapi import FastAPI\napp = FastAPI()\n")
    _write(tmp_path / "backend" / "Dockerfile", "FROM python:3.12\n")
    _write(
        tmp_path / "docker-compose.yml",
        "services:\n  frontend:\n    build:\n      context: ./frontend\n  backend:\n    build:\n      context: ./backend\n",
    )
    _write(tmp_path / "docs" / "README.md", "# docs only\n" + ("word " * 20))
    _write(tmp_path / "shared" / "types.ts", "export type Id = string;\n")

    plan = classify_project(tmp_path, repo_name="demo-monorepo")
    roles = {f.name: f.role for f in plan.folders}

    assert roles["frontend"] == "container"
    assert roles["backend"] == "container"
    assert roles["shared"] == "shared"
    assert roles["docs"] == "ignore"
    assert plan.style == "service_monorepo"
    assert "container" in plan.summary


def test_feature_modules_domain_folders(tmp_path: Path) -> None:
    for name in ("auth", "billing", "notifications"):
        _write(tmp_path / name / "service.py", f"class {name.title()}Service: pass\n")
        _write(tmp_path / name / "models.py", f"class {name.title()}Model: pass\n")
        _write(tmp_path / name / "api.py", f"def handle_{name}(): pass\n")

    plan = classify_project(tmp_path, repo_name="domain-app")
    roles = {f.name: f.role for f in plan.folders}

    assert roles["auth"] == "component"
    assert roles["billing"] == "component"
    assert roles["notifications"] == "component"
    assert plan.style == "feature_modules"
    assert set(plan.scopes_for_role("component")) >= {"auth", "billing", "notifications"}


def test_nested_subfolders_under_container(tmp_path: Path) -> None:
    _write(
        tmp_path / "backend" / "package.json",
        json.dumps({"scripts": {"start": "node server.js"}}),
    )
    _write(tmp_path / "backend" / "Dockerfile", "FROM node:20\n")
    _write(tmp_path / "backend" / "server.js", "console.log(1)\n")
    _write(tmp_path / "backend" / "auth" / "login.ts", "export function login() {}\n")
    _write(tmp_path / "backend" / "auth" / "token.ts", "export function token() {}\n")
    _write(tmp_path / "backend" / "billing" / "invoice.ts", "export class Invoice {}\n")
    _write(tmp_path / "backend" / "billing" / "pricing.ts", "export class Pricing {}\n")

    plan = classify_project(tmp_path, repo_name="nested")
    backend = next(f for f in plan.folders if f.name == "backend")
    assert backend.role == "container"
    child_roles = {c.name: c.role for c in backend.children}
    assert child_roles.get("auth") == "component"
    assert child_roles.get("billing") == "component"


def test_llm_refine_overrides_ambiguous(tmp_path: Path) -> None:
    _write(tmp_path / "workers" / "job.py", "def run(): pass\n")
    _write(tmp_path / "workers" / "queue.py", "def push(): pass\n")

    plan = classify_project(tmp_path, repo_name="workers-app")

    class FakeAdapter:
        def chat_json(self, system_prompt, user_prompt, model=None, temperature=0.1):
            return {
                "labels": [
                    {
                        "path": "workers",
                        "role": "container",
                        "reason": "background worker process",
                    }
                ]
            }

    refined = refine_with_llm(plan, FakeAdapter())
    workers = next(f for f in refined.folders if f.name == "workers")
    assert workers.role == "container"
    assert workers.refined_by_llm is True
