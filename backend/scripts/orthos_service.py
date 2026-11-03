#!/usr/bin/env python3
"""Orthos headless service CLI — generate docs and/or publish to Confluence.

Intended for CI (PR merge) and other workflows that treat Orthos as a module.

Examples:
  # Generate docs for the current checkout
  python scripts/orthos_service.py generate --project-path /path/to/repo

  # Publish an existing documentation/ folder
  python scripts/orthos_service.py publish --output-folder /path/to/repo/documentation \\
      --page-url "https://org.atlassian.net/wiki/spaces/X/pages/123"

  # Generate + publish in one shot
  python scripts/orthos_service.py pipeline --project-path /path/to/repo --publish \\
      --page-id 123456

  # Call a remote Orthos API instead of in-process
  python scripts/orthos_service.py pipeline --project-path /path/to/repo --publish \\
      --page-id 123456 --api-url http://orthos-backend:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _http_json(method: str, url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}: {detail[:1200]}") from exc


def cmd_generate(args: argparse.Namespace) -> dict:
    project = Path(args.project_path).expanduser().resolve()
    output = (
        Path(args.output_folder).expanduser().resolve()
        if args.output_folder
        else project / "documentation"
    )
    if args.api_url:
        return _http_json(
            "POST",
            f"{args.api_url.rstrip('/')}/api/docs/generate",
            {"project_path": str(project), "output_folder": str(output)},
        )

    from app.doc_agent import documentation_agent

    return documentation_agent.generate_documentation_suite(
        project_path=project,
        output_folder=output,
    )


def cmd_publish(args: argparse.Namespace) -> dict:
    output = Path(args.output_folder).expanduser().resolve()
    payload = {
        "output_folder": str(output),
        "page_id": args.page_id,
        "page_url": args.page_url,
        "prefer": args.prefer,
        "title": args.title,
    }
    if args.api_url:
        return _http_json(
            "POST",
            f"{args.api_url.rstrip('/')}/api/docs/publish",
            payload,
        )

    from app.confluence_publish import publish_documentation_to_confluence

    return publish_documentation_to_confluence(
        output,
        page_id=args.page_id,
        page_url=args.page_url,
        prefer=args.prefer,
        title_override=args.title,
    )


def cmd_pipeline(args: argparse.Namespace) -> dict:
    project = Path(args.project_path).expanduser().resolve()
    output = (
        Path(args.output_folder).expanduser().resolve()
        if args.output_folder
        else project / "documentation"
    )
    payload = {
        "project_path": str(project),
        "output_folder": str(output),
        "publish": bool(args.publish),
        "page_id": args.page_id,
        "page_url": args.page_url,
        "prefer": args.prefer,
        "title": args.title,
    }
    if args.api_url:
        return _http_json(
            "POST",
            f"{args.api_url.rstrip('/')}/api/docs/pipeline",
            payload,
        )

    from app.confluence_publish import publish_documentation_to_confluence
    from app.doc_agent import documentation_agent

    generated = documentation_agent.generate_documentation_suite(
        project_path=project,
        output_folder=output,
    )
    result: dict = {"generate": generated, "publish": None}
    if args.publish:
        result["publish"] = publish_documentation_to_confluence(
            output,
            page_id=args.page_id,
            page_url=args.page_url,
            prefer=args.prefer,
            title_override=args.title,
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orthos_service",
        description="Orthos headless docs service (generate / publish / pipeline)",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="Optional Orthos backend base URL. When set, calls HTTP APIs instead of in-process.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="Generate Confluence-ready documentation suite")
    p_gen.add_argument("--project-path", required=True)
    p_gen.add_argument("--output-folder", default=None)
    p_gen.set_defaults(func=cmd_generate)

    p_pub = sub.add_parser("publish", help="Publish an existing documentation/ folder to Confluence")
    p_pub.add_argument("--output-folder", required=True)
    p_pub.add_argument("--page-id", default=None)
    p_pub.add_argument("--page-url", default=None)
    p_pub.add_argument("--prefer", default="both", choices=["both", "markdown", "png"])
    p_pub.add_argument("--title", default=None)
    p_pub.set_defaults(func=cmd_publish)

    p_pipe = sub.add_parser("pipeline", help="Generate docs and optionally publish to Confluence")
    p_pipe.add_argument("--project-path", required=True)
    p_pipe.add_argument("--output-folder", default=None)
    p_pipe.add_argument("--publish", action="store_true")
    p_pipe.add_argument("--page-id", default=None)
    p_pipe.add_argument("--page-url", default=None)
    p_pipe.add_argument("--prefer", default="both", choices=["both", "markdown", "png"])
    p_pipe.add_argument("--title", default=None)
    p_pipe.set_defaults(func=cmd_pipeline)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = args.func(args)
    # Keep CI logs readable: summarize generate payload if huge.
    if isinstance(result, dict) and "generate" in result and isinstance(result["generate"], dict):
        gen = result["generate"]
        result = {
            **result,
            "generate": {
                "agent_id": gen.get("agent_id"),
                "project_path": gen.get("project_path"),
                "output_folder": gen.get("output_folder"),
                "diagrams_generated": gen.get("diagrams_generated"),
                "total_files_written": len(gen.get("files_written") or []),
                "composite_architecture_score": (gen.get("evaluation_metrics") or {}).get(
                    "composite_architecture_score"
                ),
            },
        }
    elif isinstance(result, dict) and "files_written" in result:
        result = {
            "agent_id": result.get("agent_id"),
            "project_path": result.get("project_path"),
            "output_folder": result.get("output_folder"),
            "diagrams_generated": result.get("diagrams_generated"),
            "total_files_written": len(result.get("files_written") or []),
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
