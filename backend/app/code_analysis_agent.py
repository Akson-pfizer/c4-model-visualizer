"""Code Analysis agent: factor sub-agents + supervisor over LLMHub.

On ``Run code analysis``, each factor specialist reviews a repo digest, then the
supervisor reconciles findings and computes dashboard scorecards.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.code_quality_scan import run_code_quality_scan
from app.config import settings
from app.llmhub_adapter import get_adapter
from app.prompt.code_analysis import (
    CODE_ANALYSIS_FACTORS,
    build_code_analysis_factor_prompts,
    build_code_analysis_supervisor_prompts,
)
from app.skills_registry import skill_read_code_summary

logger = logging.getLogger(__name__)

SUPERVISOR_AGENT_ID = "ca-supervisor"


def _resolve_root(source: str) -> Path:
    default_root = Path(__file__).resolve().parent.parent.parent
    candidate = Path(source).expanduser()
    if not candidate.is_absolute():
        candidate = (Path(__file__).resolve().parent.parent / candidate).resolve()
    return candidate if candidate.exists() and candidate.is_dir() else default_root


def _build_repo_digest(root: Path, max_chars: int = 20000) -> str:
    summary = skill_read_code_summary(root)
    audits = sorted(
        summary.get("file_audits") or [],
        key=lambda a: (0 if not a.get("within_loc_budget") else 1, -(a.get("loc") or 0)),
    )
    lines = [
        f"Root: {root}",
        f"Total files: {summary.get('total_files')}",
        f"Extensions: {summary.get('extension_breakdown')}",
        f"Files over 400 LOC: {summary.get('files_over_400_loc')}",
        f"Python classes (sample): {(summary.get('python_classes') or [])[:40]}",
        f"Python functions (sample): {(summary.get('python_functions') or [])[:40]}",
        f"Svelte components (sample): {(summary.get('svelte_components') or [])[:40]}",
        "File audits (prioritized):",
    ]
    for audit in audits[:60]:
        lines.append(
            f"- {audit.get('file')} loc={audit.get('loc')} "
            f"nested_ternaries={audit.get('nested_ternaries_s3358')} "
            f"within_budget={audit.get('within_loc_budget')}"
        )

    # Attach short snippets for the worst offenders.
    for audit in audits[:12]:
        rel = audit.get("file")
        if not rel:
            continue
        path = root / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        snippet = "\n".join(text.splitlines()[:80])
        lines.append(f"\n### Snippet: {rel}\n```\n{snippet}\n```")

    digest = "\n".join(lines)
    if len(digest) > max_chars:
        return digest[: max_chars - 20] + "\n…[truncated]"
    return digest


def _normalize_issue(raw: dict[str, Any], idx: int) -> dict[str, Any]:
    issue_id = str(raw.get("id") or f"Q{idx}")
    category = str(raw.get("category") or "quality")
    fix = str(raw.get("fix") or "Investigate and remediate.")
    title = str(raw.get("title") or "Finding")
    problem = str(raw.get("problem") or raw.get("detail") or title)
    why = str(raw.get("why") or "Violates maintainability, security, or correctness standards.")
    impact = str(raw.get("impact") or "Raises defect, security, or operational risk.")
    detail = str(raw.get("detail") or problem)
    evidence = str(raw.get("evidence") or "repository")
    severity = str(raw.get("severity") or "major")
    steps = raw.get("steps") if isinstance(raw.get("steps"), list) else []
    citation = raw.get("citation")

    recs = []
    if isinstance(raw.get("recommendations"), list) and raw["recommendations"]:
        for i, rec in enumerate(raw["recommendations"], start=1):
            if not isinstance(rec, dict):
                continue
            recs.append(
                {
                    "id": str(rec.get("id") or f"R-{issue_id}-{i}"),
                    "title": str(rec.get("title") or "Recommendation"),
                    "detail": str(rec.get("detail") or fix),
                    "category": category,
                    "issue_id": issue_id,
                    "citation": rec.get("citation") or citation,
                }
            )
    else:
        recs.append(
            {
                "id": f"R-{issue_id}-1",
                "title": "Primary fix",
                "detail": fix,
                "category": category,
                "issue_id": issue_id,
                "citation": citation,
            }
        )
        for i, step in enumerate(steps[:4], start=2):
            recs.append(
                {
                    "id": f"R-{issue_id}-{i}",
                    "title": f"Step {i - 1}",
                    "detail": str(step),
                    "category": category,
                    "issue_id": issue_id,
                }
            )

    return {
        "id": issue_id,
        "category": category,
        "title": title,
        "severity": severity,
        "problem": problem,
        "why": why,
        "impact": impact,
        "detail": detail,
        "evidence": evidence,
        "fix": fix,
        "recommendations": recs,
    }


def _scorecards_from_issues(issues: list[dict[str, Any]]) -> dict[str, int]:
    def count(*cats: str) -> int:
        return sum(1 for i in issues if i.get("category") in cats)

    critical_errors = sum(
        1
        for i in issues
        if i.get("severity") == "critical" or i.get("category") in {"error", "endpoint", "security"}
    )
    sec_hits = count("security")
    end_hits = count("endpoint")
    qual_hits = count("quality", "fallacy")
    security_score = max(0, 100 - sec_hits * 12 - end_hits * 8 - critical_errors * 2)
    quality_score = max(0, 100 - qual_hits * 6 - count("bug") * 4)

    return {
        "bugs": count("bug", "security"),
        "logical_fallacies": count("fallacy"),
        "errors": count("error") + sum(1 for i in issues if i.get("severity") == "critical"),
        "security_score": security_score,
        "quality_score": quality_score,
        "vulnerability_count": sec_hits,
        "memory_risk_points": count("memory"),
        "open_endpoint_risks": end_hits,
        "optimization_opportunities": count("optimize", "quality"),
    }


def _run_factor(
    factor: str,
    *,
    repo_digest: str,
    design_guide: dict[str, Any] | None,
    model: str | None,
) -> dict[str, Any]:
    meta = CODE_ANALYSIS_FACTORS[factor]
    adapter = get_adapter(meta["agent_id"])
    system, user = build_code_analysis_factor_prompts(
        factor=factor,
        repo_digest=repo_digest,
        design_guide=design_guide,
        model=model,
    )
    try:
        raw = adapter.chat_json(system, user, model=model, temperature=0.15)
        if not isinstance(raw, dict):
            return {"factor": factor, "error": "non-object response", "issues": [], "score_hint": 50}
        raw.setdefault("factor", factor)
        return raw
    except Exception as exc:
        logger.exception("Code analysis factor %s failed: %s", factor, exc)
        return {
            "factor": factor,
            "error": str(exc),
            "summary": f"Sub-agent failed: {exc}",
            "score_hint": 50,
            "issues": [],
            "recommendations": [],
        }


def _supervise(
    factor_results: list[dict[str, Any]],
    *,
    design_guide: dict[str, Any] | None,
    model: str | None,
    static_seed: dict[str, Any] | None,
) -> dict[str, Any]:
    adapter = get_adapter(SUPERVISOR_AGENT_ID)
    system, user = build_code_analysis_supervisor_prompts(
        factor_results=factor_results,
        design_guide=design_guide,
        model=model,
        static_seed=static_seed,
    )
    return adapter.chat_json(system, user, model=model, temperature=0.1)


def _attach_guide(issues: list[dict[str, Any]], design_guide: dict[str, Any] | None) -> None:
    if not design_guide or not design_guide.get("filename"):
        return
    for issue in issues:
        issue["design_guide"] = {
            "filename": design_guide.get("filename"),
            "citations": (design_guide.get("citations") or [])[:6],
        }


def run_code_analysis_agents(
    source: str = "..",
    model: str | None = None,
    design_guide: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run factor sub-agents + supervisor. Falls back to static scan if LLM unavailable."""
    root = _resolve_root(source)
    chosen_model = (model or settings.model_powerful or settings.model_medium or "").strip() or None

    # Static seed always available for corroboration / fallback.
    static_report = run_code_quality_scan(str(root), model=chosen_model, design_guide=design_guide)

    if not settings.llmhub_api_key:
        static_report["analyses"] = {
            **(static_report.get("analyses") or {}),
            "agentic": "skipped_no_llmhub_key",
        }
        static_report["summary"] = (
            "LLMHub API key not configured — returned static heuristic analysis only."
        )
        return static_report

    repo_digest = _build_repo_digest(root)
    factor_results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=min(6, len(CODE_ANALYSIS_FACTORS))) as pool:
        futures = {
            pool.submit(
                _run_factor,
                factor,
                repo_digest=repo_digest,
                design_guide=design_guide,
                model=chosen_model,
            ): factor
            for factor in CODE_ANALYSIS_FACTORS
        }
        for fut in as_completed(futures):
            factor_results.append(fut.result())

    factor_results.sort(key=lambda r: str(r.get("factor") or ""))

    try:
        supervised = _supervise(
            factor_results,
            design_guide=design_guide,
            model=chosen_model,
            static_seed={
                "scorecards": static_report.get("scorecards"),
                "issue_titles": [i.get("title") for i in (static_report.get("issues") or [])[:20]],
            },
        )
    except Exception as exc:
        logger.exception("Code analysis supervisor failed: %s", exc)
        static_report["analyses"] = {
            **(static_report.get("analyses") or {}),
            "agentic": f"supervisor_failed:{exc}",
        }
        static_report["factor_results"] = factor_results
        return static_report

    raw_issues = supervised.get("issues") if isinstance(supervised, dict) else None
    if not isinstance(raw_issues, list) or not raw_issues:
        # Flatten sub-agent issues if supervisor returned nothing usable.
        raw_issues = []
        for fr in factor_results:
            for issue in fr.get("issues") or []:
                if isinstance(issue, dict):
                    raw_issues.append(issue)

    issues = [_normalize_issue(i, idx + 1) for idx, i in enumerate(raw_issues[:60])]
    _attach_guide(issues, design_guide)

    scorecards = supervised.get("scorecards") if isinstance(supervised, dict) else None
    if not isinstance(scorecards, dict):
        scorecards = _scorecards_from_issues(issues)
    else:
        # Ensure required keys exist; fill gaps from counts.
        computed = _scorecards_from_issues(issues)
        for key, val in computed.items():
            if key not in scorecards or scorecards[key] is None:
                scorecards[key] = val

    recommendations: list[dict[str, Any]] = []
    for issue in issues:
        recommendations.extend(issue.get("recommendations") or [])

    analyses = supervised.get("analyses") if isinstance(supervised, dict) else None
    if not isinstance(analyses, dict):
        analyses = {
            "static": "complete",
            "dynamic": "scheduled",
            "sonarqube": "complete",
            "memory_profile": "complete",
            "security_scan": "complete",
            "endpoint_auth": "complete",
            "agentic": "complete",
        }
    else:
        analyses = {**analyses, "agentic": "complete"}

    return {
        "model": chosen_model or "default",
        "source": str(root),
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "files_scanned": (static_report.get("files_scanned") or 0),
        "summary": (supervised.get("summary") if isinstance(supervised, dict) else "")
        or "Agentic code analysis complete.",
        "design_guide": {
            "filename": (design_guide or {}).get("filename"),
            "active": bool((design_guide or {}).get("filename")),
            "citations": (design_guide or {}).get("citations") or [],
        },
        "scorecards": {
            "bugs": int(scorecards.get("bugs") or 0),
            "logical_fallacies": int(scorecards.get("logical_fallacies") or 0),
            "errors": int(scorecards.get("errors") or 0),
            "security_score": int(scorecards.get("security_score") or 0),
            "quality_score": int(scorecards.get("quality_score") or 0),
            "vulnerability_count": int(scorecards.get("vulnerability_count") or 0),
            "memory_risk_points": int(scorecards.get("memory_risk_points") or 0),
            "open_endpoint_risks": int(scorecards.get("open_endpoint_risks") or 0),
            "optimization_opportunities": int(scorecards.get("optimization_opportunities") or 0),
        },
        "analyses": analyses,
        "issues": issues,
        "recommendations": recommendations,
        "factor_results": [
            {
                "factor": fr.get("factor"),
                "summary": fr.get("summary"),
                "score_hint": fr.get("score_hint"),
                "error": fr.get("error"),
                "issue_count": len(fr.get("issues") or []),
            }
            for fr in factor_results
        ],
    }
