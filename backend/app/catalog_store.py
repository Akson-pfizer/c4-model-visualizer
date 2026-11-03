"""SQLite catalog of analyzed repositories and cached C4 payloads.

Stores metadata (last opened / analyzed) plus the full HierarchyModelResponse JSON
so the Architect Catalog can reopen a project without re-running the agents.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_catalog_id(source: str, source_type: str) -> str:
    normalized = f"{source_type}::{str(source).strip()}"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
    return f"{source_type}-{digest}"


@dataclass
class CatalogEntry:
    id: str
    source: str
    source_type: str
    repo_name: str
    display_name: str
    style: str | None
    node_count: int
    edge_count: int
    view_count: int
    first_analyzed_at: str
    last_analyzed_at: str
    last_opened_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "source_type": self.source_type,
            "repo_name": self.repo_name,
            "display_name": self.display_name,
            "style": self.style,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "view_count": self.view_count,
            "first_analyzed_at": self.first_analyzed_at,
            "last_analyzed_at": self.last_analyzed_at,
            "last_opened_at": self.last_opened_at,
        }


class CatalogStore:
    """Persistent Architect Catalog backed by SQLite."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
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
                CREATE TABLE IF NOT EXISTS analyzed_repos (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    repo_name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    style TEXT,
                    node_count INTEGER NOT NULL DEFAULT 0,
                    edge_count INTEGER NOT NULL DEFAULT 0,
                    view_count INTEGER NOT NULL DEFAULT 0,
                    first_analyzed_at TEXT NOT NULL,
                    last_analyzed_at TEXT NOT NULL,
                    last_opened_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_catalog_last_opened
                ON analyzed_repos(last_opened_at DESC)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quality_reports (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    model TEXT,
                    ran_at TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    last_updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_quality_source
                ON quality_reports(source_type, source)
                """
            )
            conn.commit()

    def _row_to_entry(self, row: sqlite3.Row) -> CatalogEntry:
        return CatalogEntry(
            id=row["id"],
            source=row["source"],
            source_type=row["source_type"],
            repo_name=row["repo_name"],
            display_name=row["display_name"],
            style=row["style"],
            node_count=int(row["node_count"] or 0),
            edge_count=int(row["edge_count"] or 0),
            view_count=int(row["view_count"] or 0),
            first_analyzed_at=row["first_analyzed_at"],
            last_analyzed_at=row["last_analyzed_at"],
            last_opened_at=row["last_opened_at"],
        )

    def list_entries(self, query: str | None = None) -> list[CatalogEntry]:
        q = (query or "").strip().lower()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, source, source_type, repo_name, display_name, style,
                       node_count, edge_count, view_count,
                       first_analyzed_at, last_analyzed_at, last_opened_at
                FROM analyzed_repos
                ORDER BY last_opened_at DESC
                """
            ).fetchall()
        entries = [self._row_to_entry(row) for row in rows]
        if not q:
            return entries
        return [
            e
            for e in entries
            if q in e.display_name.lower()
            or q in e.repo_name.lower()
            or q in e.source.lower()
            or q in (e.style or "").lower()
            or q in e.source_type.lower()
        ]

    def get_entry(self, entry_id: str) -> CatalogEntry | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, source, source_type, repo_name, display_name, style,
                       node_count, edge_count, view_count,
                       first_analyzed_at, last_analyzed_at, last_opened_at
                FROM analyzed_repos
                WHERE id = ?
                """,
                (entry_id,),
            ).fetchone()
        return self._row_to_entry(row) if row else None

    def get_payload(self, entry_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM analyzed_repos WHERE id = ?",
                (entry_id,),
            ).fetchone()
        if not row:
            return None
        try:
            data = json.loads(row["payload_json"])
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def upsert_analysis(self, payload: dict[str, Any]) -> CatalogEntry:
        source = str(payload.get("source") or "").strip()
        source_type = str(payload.get("source_type") or "local")
        if source_type not in ("local", "github"):
            source_type = "local"
        if not source:
            raise ValueError("payload.source is required")

        entry_id = make_catalog_id(source, source_type)
        repo_name = str(payload.get("repo_name") or Path(source).name or source)
        project_plan = payload.get("project_plan") or {}
        style = None
        if isinstance(project_plan, dict):
            style = project_plan.get("style")

        layers = payload.get("layers") or {}
        node_count = 0
        edge_count = 0
        if isinstance(layers, dict):
            for layer_payload in layers.values():
                if not isinstance(layer_payload, dict):
                    continue
                node_count += len(layer_payload.get("nodes") or [])
                edge_count += len(layer_payload.get("edges") or [])

        stamp = _now_iso()
        payload_json = json.dumps(payload, ensure_ascii=False)

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT view_count, first_analyzed_at FROM analyzed_repos WHERE id = ?",
                (entry_id,),
            ).fetchone()
            if existing:
                view_count = int(existing["view_count"] or 0) + 1
                first_analyzed_at = existing["first_analyzed_at"] or stamp
                conn.execute(
                    """
                    UPDATE analyzed_repos
                    SET source = ?, source_type = ?, repo_name = ?, display_name = ?,
                        style = ?, node_count = ?, edge_count = ?, view_count = ?,
                        last_analyzed_at = ?, last_opened_at = ?, payload_json = ?
                    WHERE id = ?
                    """,
                    (
                        source,
                        source_type,
                        repo_name,
                        repo_name,
                        style,
                        node_count,
                        edge_count,
                        view_count,
                        stamp,
                        stamp,
                        payload_json,
                        entry_id,
                    ),
                )
            else:
                view_count = 1
                first_analyzed_at = stamp
                conn.execute(
                    """
                    INSERT INTO analyzed_repos (
                        id, source, source_type, repo_name, display_name, style,
                        node_count, edge_count, view_count,
                        first_analyzed_at, last_analyzed_at, last_opened_at, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry_id,
                        source,
                        source_type,
                        repo_name,
                        repo_name,
                        style,
                        node_count,
                        edge_count,
                        view_count,
                        first_analyzed_at,
                        stamp,
                        stamp,
                        payload_json,
                    ),
                )
            conn.commit()

        return CatalogEntry(
            id=entry_id,
            source=source,
            source_type=source_type,
            repo_name=repo_name,
            display_name=repo_name,
            style=style,
            node_count=node_count,
            edge_count=edge_count,
            view_count=view_count,
            first_analyzed_at=first_analyzed_at,
            last_analyzed_at=stamp,
            last_opened_at=stamp,
        )

    def open_entry(self, entry_id: str) -> tuple[CatalogEntry, dict[str, Any]] | None:
        stamp = _now_iso()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, source, source_type, repo_name, display_name, style,
                       node_count, edge_count, view_count,
                       first_analyzed_at, last_analyzed_at, last_opened_at, payload_json
                FROM analyzed_repos
                WHERE id = ?
                """,
                (entry_id,),
            ).fetchone()
            if not row:
                return None
            view_count = int(row["view_count"] or 0) + 1
            conn.execute(
                """
                UPDATE analyzed_repos
                SET last_opened_at = ?, view_count = ?
                WHERE id = ?
                """,
                (stamp, view_count, entry_id),
            )
            conn.commit()

        try:
            payload = json.loads(row["payload_json"])
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None

        entry = CatalogEntry(
            id=row["id"],
            source=row["source"],
            source_type=row["source_type"],
            repo_name=row["repo_name"],
            display_name=row["display_name"],
            style=row["style"],
            node_count=int(row["node_count"] or 0),
            edge_count=int(row["edge_count"] or 0),
            view_count=view_count,
            first_analyzed_at=row["first_analyzed_at"],
            last_analyzed_at=row["last_analyzed_at"],
            last_opened_at=stamp,
        )
        return entry, payload

    def upsert_quality_report(
        self,
        source: str,
        source_type: str,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        """Cache a Code Analysis report for a repo; a new run replaces the previous one."""
        clean_source = str(source or "").strip()
        clean_type = str(source_type or "local").strip().lower()
        if clean_type not in ("local", "github"):
            clean_type = "local"
        if not clean_source:
            raise ValueError("source is required to cache a quality report")

        entry_id = make_catalog_id(clean_source, clean_type)
        stamp = _now_iso()
        ran_at = str(report.get("ran_at") or stamp)
        model = report.get("model")
        report_json = json.dumps(report, ensure_ascii=False)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO quality_reports (
                    id, source, source_type, model, ran_at, report_json, last_updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source = excluded.source,
                    source_type = excluded.source_type,
                    model = excluded.model,
                    ran_at = excluded.ran_at,
                    report_json = excluded.report_json,
                    last_updated_at = excluded.last_updated_at
                """,
                (
                    entry_id,
                    clean_source,
                    clean_type,
                    str(model) if model is not None else None,
                    ran_at,
                    report_json,
                    stamp,
                ),
            )
            conn.commit()

        return {
            "id": entry_id,
            "source": clean_source,
            "source_type": clean_type,
            "model": model,
            "ran_at": ran_at,
            "last_updated_at": stamp,
            "cached": True,
        }

    def get_quality_report(
        self,
        *,
        entry_id: str | None = None,
        source: str | None = None,
        source_type: str = "local",
    ) -> dict[str, Any] | None:
        """Return the latest cached Code Analysis report for a catalog repo, if any."""
        resolved_id = (entry_id or "").strip()
        if not resolved_id:
            clean_source = str(source or "").strip()
            clean_type = str(source_type or "local").strip().lower()
            if clean_type not in ("local", "github"):
                clean_type = "local"
            if not clean_source:
                return None
            resolved_id = make_catalog_id(clean_source, clean_type)

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, source, source_type, model, ran_at, report_json, last_updated_at
                FROM quality_reports
                WHERE id = ?
                """,
                (resolved_id,),
            ).fetchone()
        if not row:
            return None
        try:
            report = json.loads(row["report_json"])
        except json.JSONDecodeError:
            return None
        if not isinstance(report, dict):
            return None
        return {
            "id": row["id"],
            "source": row["source"],
            "source_type": row["source_type"],
            "model": row["model"],
            "ran_at": row["ran_at"],
            "last_updated_at": row["last_updated_at"],
            "cached": True,
            "report": report,
        }

    def delete_entry(self, entry_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM analyzed_repos WHERE id = ?", (entry_id,))
            conn.execute("DELETE FROM quality_reports WHERE id = ?", (entry_id,))
            conn.commit()
            return cur.rowcount > 0

    def clear(self) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM analyzed_repos")
            conn.execute("DELETE FROM quality_reports")
            conn.commit()
            return cur.rowcount

    def get_profile_name(self, default: str = "Architect") -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM profile_meta WHERE key = 'display_name'"
            ).fetchone()
        if row and str(row["value"]).strip():
            return str(row["value"]).strip()
        return default

    def set_profile_name(self, name: str) -> str:
        clean = (name or "").strip() or "Architect"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO profile_meta (key, value) VALUES ('display_name', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (clean,),
            )
            conn.commit()
        return clean


_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = _BACKEND_ROOT / "data" / "catalog" / "catalog.db"

catalog_store = CatalogStore(_DEFAULT_DB)
