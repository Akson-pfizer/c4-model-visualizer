"""Persist uploaded Design Guide docs used as the Code Analysis bible / citations."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_DIR = _ROOT / "data" / "design_guides"
_META = _DIR / "active.json"
_ALLOWED = {".md", ".txt", ".pdf", ".docx", ".html", ".json"}


def _ensure_dir() -> None:
    _DIR.mkdir(parents=True, exist_ok=True)


def _excerpt_from_bytes(name: str, raw: bytes, limit: int = 4000) -> tuple[str, list[str]]:
    text = ""
    suffix = Path(name).suffix.lower()
    if suffix in {".md", ".txt", ".html", ".json"}:
        text = raw.decode("utf-8", errors="ignore")
    elif suffix == ".pdf":
        # Lightweight extract: keep printable ASCII/UTF fragments from binary.
        text = re.sub(r"[^\x09\x0a\x0d\x20-\x7e\u00a0-\uffff]", " ", raw.decode("latin-1", errors="ignore"))
        text = re.sub(r"\s+", " ", text)
    else:
        text = raw.decode("utf-8", errors="ignore")

    text = text.strip()
    excerpt = text[:limit]
    # Pull short citation-like headings / numbered rules.
    citations: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or len(s) < 8:
            continue
        if re.match(r"^(#{1,3}\s+|\d+[\).\s]+|[A-Z][A-Za-z ].{8,80})$", s):
            citations.append(s.lstrip("# ").strip()[:120])
        if len(citations) >= 12:
            break
    if not citations and excerpt:
        citations = [excerpt[:120] + ("…" if len(excerpt) > 120 else "")]
    return excerpt, citations


def get_active_guide() -> dict[str, Any] | None:
    _ensure_dir()
    if not _META.exists():
        return None
    try:
        data = json.loads(_META.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    path = _DIR / str(data.get("stored_as") or "")
    if not path.exists():
        return None
    return data


def save_guide(filename: str, raw: bytes) -> dict[str, Any]:
    _ensure_dir()
    safe = re.sub(r"[^\w.\-]+", "_", Path(filename).name) or "design-guide.txt"
    suffix = Path(safe).suffix.lower()
    if suffix not in _ALLOWED:
        raise ValueError(f"Unsupported file type {suffix or '(none)'}. Use md, txt, pdf, docx, html, or json.")
    if len(raw) > 8_000_000:
        raise ValueError("Design guide exceeds 8 MB limit.")

    stored_as = f"active{suffix}"
    target = _DIR / stored_as
    # Clear previous active binaries.
    for old in _DIR.glob("active.*"):
        if old.name != "active.json":
            try:
                old.unlink()
            except OSError:
                pass
    target.write_bytes(raw)
    excerpt, citations = _excerpt_from_bytes(safe, raw)
    meta = {
        "filename": safe,
        "stored_as": stored_as,
        "bytes": len(raw),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "excerpt": excerpt,
        "citations": citations,
    }
    _META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def clear_guide() -> None:
    _ensure_dir()
    if _META.exists():
        _META.unlink(missing_ok=True)
    for old in _DIR.glob("active.*"):
        try:
            old.unlink()
        except OSError:
            pass


def guide_for_analysis() -> dict[str, Any] | None:
    meta = get_active_guide()
    if not meta:
        return None
    return {
        "filename": meta.get("filename"),
        "excerpt": meta.get("excerpt") or "",
        "citations": meta.get("citations") or [],
    }
