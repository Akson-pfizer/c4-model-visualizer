"""Publish Orthos documentation artifacts to a Confluence Cloud/Server page.

Designed for headless CI use:
  1. Upload PNG diagram attachments
  2. Update the target page body with Markdown (macro) + image gallery

Auth / config (environment):
  CONFLUENCE_BASE_URL   e.g. https://your-org.atlassian.net/wiki
  CONFLUENCE_EMAIL      Atlassian account email (Cloud)
  CONFLUENCE_API_TOKEN  Atlassian API token (Cloud) or PAT (Server/DC)
  CONFLUENCE_PAGE_ID    optional default page id
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class ConfluencePublishError(RuntimeError):
    """Raised when Confluence rejects a request or config is incomplete."""


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def resolve_confluence_config(
    *,
    base_url: str | None = None,
    email: str | None = None,
    api_token: str | None = None,
    page_id: str | None = None,
    page_url: str | None = None,
) -> dict[str, str]:
    base = (base_url or _env("CONFLUENCE_BASE_URL")).rstrip("/")
    user = email or _env("CONFLUENCE_EMAIL") or _env("CONFLUENCE_USER")
    token = api_token or _env("CONFLUENCE_API_TOKEN") or _env("CONFLUENCE_TOKEN")
    pid = page_id or _env("CONFLUENCE_PAGE_ID")
    url = page_url or _env("CONFLUENCE_PAGE_URL")

    if url and not pid:
        pid = extract_page_id_from_url(url) or ""
    if url and not base:
        base = extract_base_url_from_page_url(url) or ""

    missing = [
        name
        for name, value in (
            ("CONFLUENCE_BASE_URL", base),
            ("CONFLUENCE_EMAIL", user),
            ("CONFLUENCE_API_TOKEN", token),
            ("CONFLUENCE_PAGE_ID / page URL", pid),
        )
        if not value
    ]
    if missing:
        raise ConfluencePublishError(
            "Missing Confluence settings: " + ", ".join(missing)
        )

    return {
        "base_url": base,
        "email": user,
        "api_token": token,
        "page_id": pid,
    }


def extract_page_id_from_url(page_url: str) -> str | None:
    """Best-effort parse of Confluence Cloud/Server page URLs."""
    text = (page_url or "").strip()
    if not text:
        return None
    # /pages/123456/... or pageId=123456
    for pattern in (
        r"/pages/(\d+)",
        r"[?&]pageId=(\d+)",
        r"/wiki/spaces/[^/]+/pages/(\d+)",
        r"/display/.+/(\d+)$",
    ):
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    # bare numeric id
    if text.isdigit():
        return text
    return None


def extract_base_url_from_page_url(page_url: str) -> str | None:
    try:
        parsed = urllib.parse.urlparse(page_url)
        if not parsed.scheme or not parsed.netloc:
            return None
        path = parsed.path or ""
        # Keep /wiki when present (Cloud).
        if "/wiki" in path:
            wiki = path.split("/wiki", 1)[0] + "/wiki"
            return f"{parsed.scheme}://{parsed.netloc}{wiki}".rstrip("/")
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:  # noqa: BLE001
        return None


class ConfluenceClient:
    def __init__(self, base_url: str, email: str, api_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        raw = f"{email}:{api_token}".encode("utf-8")
        self._auth = "Basic " + base64.b64encode(raw).decode("ascii")

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        query: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        req_headers = {
            "Authorization": self._auth,
            "Accept": "application/json",
            "User-Agent": "orthos-confluence-publish/1.0",
        }
        if headers:
            req_headers.update(headers)
        request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ConfluencePublishError(
                f"Confluence {method} {path} failed ({exc.code}): {detail[:800]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ConfluencePublishError(f"Confluence unreachable: {exc}") from exc

    def get_page(self, page_id: str) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/rest/api/content/{page_id}",
            query={"expand": "body.storage,version,space"},
        )

    def update_page(
        self,
        page_id: str,
        *,
        title: str,
        storage_html: str,
        version: int,
    ) -> dict[str, Any]:
        payload = {
            "id": str(page_id),
            "type": "page",
            "title": title,
            "version": {"number": int(version)},
            "body": {
                "storage": {
                    "value": storage_html,
                    "representation": "storage",
                }
            },
        }
        data = json.dumps(payload).encode("utf-8")
        return self._request(
            "PUT",
            f"/rest/api/content/{page_id}",
            data=data,
            headers={"Content-Type": "application/json"},
        )

    def upload_attachment(self, page_id: str, file_path: Path) -> dict[str, Any]:
        """Upload or replace an attachment (X-Atlassian-Token: no-check)."""
        path = Path(file_path)
        if not path.is_file():
            raise ConfluencePublishError(f"Attachment not found: {path}")

        boundary = "----OrthosBoundary7MA4YWxkTrZu0gW"
        filename = path.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        file_bytes = path.read_bytes()

        body = b"".join(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                ).encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                file_bytes,
                b"\r\n",
                f"--{boundary}--\r\n".encode(),
            ]
        )

        # Prefer update-if-exists via filename query when supported; Cloud uses POST.
        return self._request(
            "POST",
            f"/rest/api/content/{page_id}/child/attachment",
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "X-Atlassian-Token": "no-check",
            },
        )


def _markdown_to_storage(markdown: str, png_names: list[str]) -> str:
    """Wrap markdown in Confluence Markdown macro + append PNG gallery."""
    safe_md = markdown.replace("]]>", "]]]]><![CDATA[>")
    parts = [
        '<ac:structured-macro ac:name="markdown" ac:schema-version="1">',
        "<ac:plain-text-body><![CDATA[",
        safe_md.strip(),
        "]]></ac:plain-text-body>",
        "</ac:structured-macro>",
        "<hr />",
        "<h2>Architecture diagrams (PNG)</h2>",
    ]
    for name in png_names:
        parts.extend(
            [
                "<p>",
                f"<strong>{Path(name).stem}</strong><br />",
                "<ac:image ac:width=\"800\">",
                f'<ri:attachment ri:filename="{name}" />',
                "</ac:image>",
                "</p>",
            ]
        )
    return "\n".join(parts)


def collect_doc_artifacts(output_folder: str | Path) -> dict[str, Any]:
    root = Path(output_folder).expanduser().resolve()
    md = root / "CONFLUENCE_ARCHITECTURE_DOCUMENTATION.md"
    png_dir = root / "images" / "png"
    pngs = sorted(png_dir.glob("*.png")) if png_dir.is_dir() else []
    return {
        "output_folder": str(root),
        "markdown_path": str(md) if md.is_file() else None,
        "png_paths": [str(p) for p in pngs],
        "png_names": [p.name for p in pngs],
    }


def publish_documentation_to_confluence(
    output_folder: str | Path,
    *,
    page_id: str | None = None,
    page_url: str | None = None,
    base_url: str | None = None,
    email: str | None = None,
    api_token: str | None = None,
    prefer: str = "both",
    title_override: str | None = None,
) -> dict[str, Any]:
    """Upload PNGs and update the Confluence page from Orthos doc output."""
    cfg = resolve_confluence_config(
        base_url=base_url,
        email=email,
        api_token=api_token,
        page_id=page_id,
        page_url=page_url,
    )
    artifacts = collect_doc_artifacts(output_folder)
    if not artifacts["markdown_path"] and prefer in ("markdown", "both", "md"):
        raise ConfluencePublishError(
            "CONFLUENCE_ARCHITECTURE_DOCUMENTATION.md not found in output_folder. "
            "Run /api/docs/generate first."
        )
    if not artifacts["png_paths"] and prefer in ("png", "both"):
        raise ConfluencePublishError(
            "No PNG diagrams found under images/png. Run /api/docs/generate first."
        )

    client = ConfluenceClient(cfg["base_url"], cfg["email"], cfg["api_token"])
    page = client.get_page(cfg["page_id"])
    title = title_override or page.get("title") or "Orthos Architecture Documentation"
    current_version = int((page.get("version") or {}).get("number") or 1)

    uploaded: list[str] = []
    if prefer in ("png", "both"):
        for png in artifacts["png_paths"]:
            client.upload_attachment(cfg["page_id"], Path(png))
            uploaded.append(Path(png).name)

    markdown = ""
    if artifacts["markdown_path"]:
        markdown = Path(artifacts["markdown_path"]).read_text(encoding="utf-8")
    if prefer == "png":
        # Minimal body: image gallery only.
        storage = _markdown_to_storage(
            "# Architecture diagrams\n\nUpdated automatically by Orthos.",
            artifacts["png_names"],
        )
    else:
        storage = _markdown_to_storage(markdown, artifacts["png_names"] if prefer != "markdown" else [])

    updated = client.update_page(
        cfg["page_id"],
        title=title,
        storage_html=storage,
        version=current_version + 1,
    )

    webui = (
        ((updated.get("_links") or {}).get("base") or cfg["base_url"])
        + ((updated.get("_links") or {}).get("webui") or f"/pages/{cfg['page_id']}")
    )
    return {
        "status": "published",
        "page_id": cfg["page_id"],
        "title": title,
        "version": (updated.get("version") or {}).get("number"),
        "page_url": webui,
        "attachments_uploaded": uploaded,
        "prefer": prefer,
        "output_folder": artifacts["output_folder"],
        "markdown_used": bool(artifacts["markdown_path"]),
        "png_count": len(artifacts["png_names"]),
    }
