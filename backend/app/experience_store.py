"""Lightweight SQLite experience databases for specialist layer agents.

Each Context / Container / Component / Code subagent keeps a local SQLite DB of
prior *code-reading experiences* keyed by repository fingerprint. Retrieved
experiences are injected into LLM prompts to refine code deciphering on repeat
analyses of the same (or similar) repositories.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CodeExperience:
    repo_fingerprint: str
    repo_name: str
    layer: str
    file_path: str
    symbol_name: str
    kind: str
    summary: str
    technology: str
    parent_hint: str
    raw_snippet: str = ""


def fingerprint_repo(repo_name: str, file_paths: list[str] | list[Path]) -> str:
    """Stable short fingerprint from repo name + sorted relative file paths."""
    normalized = sorted(str(p).replace("\\", "/") for p in file_paths)
    digest = hashlib.sha256()
    digest.update(repo_name.encode("utf-8"))
    digest.update(b"\0")
    for path in normalized[:500]:
        digest.update(path.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()[:16]


class ExperienceStore:
    """Per-layer SQLite store of code-reading experiences."""

    def __init__(self, db_path: Path, layer: str) -> None:
        self.db_path = Path(db_path)
        self.layer = layer
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS code_experiences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_fingerprint TEXT NOT NULL,
                    repo_name TEXT NOT NULL,
                    layer TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    symbol_name TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '',
                    technology TEXT NOT NULL DEFAULT '',
                    parent_hint TEXT NOT NULL DEFAULT '',
                    raw_snippet TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    UNIQUE(repo_fingerprint, layer, file_path, symbol_name)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_exp_repo_layer
                ON code_experiences(repo_fingerprint, layer)
                """
            )
            conn.commit()

    def remember(self, experiences: list[CodeExperience]) -> int:
        if not experiences:
            return 0
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (
                exp.repo_fingerprint,
                exp.repo_name,
                exp.layer,
                exp.file_path,
                exp.symbol_name,
                exp.kind,
                exp.summary,
                exp.technology,
                exp.parent_hint,
                exp.raw_snippet[:2000],
                now,
            )
            for exp in experiences
        ]
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO code_experiences (
                    repo_fingerprint, repo_name, layer, file_path, symbol_name,
                    kind, summary, technology, parent_hint, raw_snippet, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(repo_fingerprint, layer, file_path, symbol_name)
                DO UPDATE SET
                    kind=excluded.kind,
                    summary=excluded.summary,
                    technology=excluded.technology,
                    parent_hint=excluded.parent_hint,
                    raw_snippet=excluded.raw_snippet,
                    created_at=excluded.created_at
                """,
                rows,
            )
            conn.commit()
            return len(rows)

    def recall(
        self,
        repo_fingerprint: str,
        *,
        limit: int = 24,
    ) -> list[CodeExperience]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT repo_fingerprint, repo_name, layer, file_path, symbol_name,
                       kind, summary, technology, parent_hint, raw_snippet
                FROM code_experiences
                WHERE repo_fingerprint = ? AND layer = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (repo_fingerprint, self.layer, limit),
            ).fetchall()
        return [
            CodeExperience(
                repo_fingerprint=row["repo_fingerprint"],
                repo_name=row["repo_name"],
                layer=row["layer"],
                file_path=row["file_path"],
                symbol_name=row["symbol_name"],
                kind=row["kind"],
                summary=row["summary"],
                technology=row["technology"],
                parent_hint=row["parent_hint"],
                raw_snippet=row["raw_snippet"],
            )
            for row in rows
        ]

    def recall_as_prompt_block(
        self,
        repo_fingerprint: str,
        *,
        limit: int = 24,
    ) -> str:
        memories = self.recall(repo_fingerprint, limit=limit)
        if not memories:
            return ""
        payload = [
            {
                "file": m.file_path,
                "symbol": m.symbol_name,
                "kind": m.kind,
                "technology": m.technology,
                "summary": m.summary,
                "parent_hint": m.parent_hint,
            }
            for m in memories
        ]
        return (
            "\nPrior code-reading experiences for this repository "
            f"(layer={self.layer}). Reuse naming, technologies, and parent "
            "hints when they still match the source — refine rather than "
            "reinvent:\n"
            f"{json.dumps(payload, indent=2)}\n"
        )

    def remember_from_extraction(
        self,
        *,
        repo_fingerprint: str,
        repo_name: str,
        extraction: Any,
    ) -> int:
        """Persist node-level decipher experiences from an ``LLMExtraction``."""
        experiences: list[CodeExperience] = []
        nodes = getattr(extraction, "nodes", None) or []
        for node in nodes:
            data = getattr(node, "data", None)
            if data is None:
                continue
            experiences.append(
                CodeExperience(
                    repo_fingerprint=repo_fingerprint,
                    repo_name=repo_name,
                    layer=self.layer,
                    file_path=str(node.id),
                    symbol_name=str(getattr(data, "name", "") or node.id),
                    kind=str(getattr(data, "kind", "") or ""),
                    summary=str(getattr(data, "description", "") or "")[:800],
                    technology=str(getattr(data, "technology", "") or ""),
                    parent_hint=str(getattr(data, "parentNodeId", "") or ""),
                )
            )
        return self.remember(experiences)
