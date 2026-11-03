"""Code Analysis agent prompts — factor sub-agents + supervisor.

Dashboard surfaces these factors as scorecards / issue filters:
bugs, logical fallacies, errors, security, quality, vulnerabilities,
memory risk, open endpoints, optimization.
"""

from __future__ import annotations

from typing import Any

CODE_ANALYSIS_FACTORS: dict[str, dict[str, str]] = {
    "quality": {
        "agent_id": "ca-subagent-quality",
        "label": "Sonar-style quality / maintainability",
        "focus": (
            "File size budgets (~400 LOC), cognitive complexity, nested ternaries (S3358), "
            "duplication, dead code, naming, and maintainability smells."
        ),
    },
    "security": {
        "agent_id": "ca-subagent-security",
        "label": "Security & vulnerabilities",
        "focus": (
            "Injection sinks (SQL/HTML/eval), XSS, secrets in source, unsafe deserialization, "
            "and CVE-class patterns. Produce a security score intuition 0–100."
        ),
    },
    "memory": {
        "agent_id": "ca-subagent-memory",
        "label": "Memory profiling / leak risks",
        "focus": (
            "Unbounded caches, globals that grow, missing dispose of listeners/intervals, "
            "and long-lived references that retain heap."
        ),
    },
    "endpoint": {
        "agent_id": "ca-subagent-endpoint",
        "label": "Endpoint auth & open access",
        "focus": (
            "HTTP/API routes lacking authentication/authorization, overly open CORS, "
            "missing input validation, and injectable or anonymously reachable surfaces."
        ),
    },
    "bugs_fallacies": {
        "agent_id": "ca-subagent-bugs",
        "label": "Bugs & logical fallacies",
        "focus": (
            "Likely functional bugs, always-true/false branches, bare except/swallow, "
            "TODO-fix-later stubs, race conditions, and incorrect control flow."
        ),
    },
    "optimize": {
        "agent_id": "ca-subagent-optimize",
        "label": "Optimization opportunities",
        "focus": (
            "Hot-path inefficiencies, N+1 queries, redundant work, oversized bundles/modules, "
            "and concrete optimization recommendations."
        ),
    },
}

_FACTOR_SYSTEM = """You are `{agent_id}`, a specialist Code Analysis sub-agent for Orthos.

Factor under review: {label}
Focus: {focus}

You receive a repository digest and an optional Design Guide (bible). Treat the Design Guide
as authoritative best-practice and cite it when relevant.

Return STRICT JSON only (no markdown fences) with this shape:
{{
  "factor": "{factor}",
  "summary": "2-4 sentences on what you found",
  "score_hint": 0,
  "issues": [
    {{
      "category": "one of: quality|security|memory|endpoint|bug|fallacy|error|optimize",
      "title": "short title",
      "severity": "critical|major|minor|info",
      "problem": "what is wrong",
      "why": "why it matters / which standard or guide rule it breaks",
      "impact": "what happens if unfixed",
      "evidence": "path or symbol",
      "fix": "concrete remediation",
      "steps": ["step 1", "step 2"],
      "citation": "optional design-guide quote or rule id"
    }}
  ],
  "recommendations": [
    {{"title": "string", "detail": "string"}}
  ]
}}

Rules:
- Prefer evidence grounded in the digest; do not invent file paths that are not hinted.
- Return 3–10 high-signal issues (empty array only if truly clean).
- score_hint: 100 = excellent for this factor, 0 = severe problems.
- category must match the issue type (use bug or fallacy under bugs_fallacies).
"""

CODE_ANALYSIS_SUPERVISOR_SYSTEM = """You are `ca-supervisor`, the Code Analysis supervisor for Orthos.

You receive JSON findings from specialist sub-agents (quality, security, memory, endpoint,
bugs/fallacies, optimize) plus optional Design Guide metadata.

Your job:
1. Deduplicate / reconcile conflicting findings.
2. Validate each issue has problem, why, impact, evidence, fix.
3. Compute dashboard scorecards from the consolidated set.
4. Attach recommendations mapped to each issue id.

Return STRICT JSON only:
{
  "summary": "executive summary ≤120 words",
  "scorecards": {
    "bugs": 0,
    "logical_fallacies": 0,
    "errors": 0,
    "security_score": 0,
    "quality_score": 0,
    "vulnerability_count": 0,
    "memory_risk_points": 0,
    "open_endpoint_risks": 0,
    "optimization_opportunities": 0
  },
  "issues": [
    {
      "id": "Q1",
      "category": "quality|security|memory|endpoint|bug|fallacy|error|optimize",
      "title": "string",
      "severity": "critical|major|minor|info",
      "problem": "string",
      "why": "string",
      "impact": "string",
      "detail": "string",
      "evidence": "string",
      "fix": "string",
      "recommendations": [
        {"id": "R-Q1-1", "title": "string", "detail": "string", "category": "string", "issue_id": "Q1", "citation": "optional"}
      ]
    }
  ],
  "analyses": {
    "static": "complete",
    "dynamic": "scheduled|complete",
    "sonarqube": "complete",
    "memory_profile": "complete",
    "security_scan": "complete",
    "endpoint_auth": "complete"
  }
}

Scoring rules:
- bugs / logical_fallacies / errors / vulnerability_count / memory_risk_points /
  open_endpoint_risks / optimization_opportunities = counts of matching issues.
- security_score / quality_score = 0–100 (100 best). Derive from severity mix and sub-agent score_hints.
- Cap issues at 60, prefer critical/major first.
"""


def build_code_analysis_factor_prompts(
    *,
    factor: str,
    repo_digest: str,
    design_guide: dict[str, Any] | None = None,
    model: str | None = None,
) -> tuple[str, str]:
    meta = CODE_ANALYSIS_FACTORS[factor]
    system = _FACTOR_SYSTEM.format(
        agent_id=meta["agent_id"],
        label=meta["label"],
        focus=meta["focus"],
        factor=factor,
    )
    guide_block = "No design guide uploaded."
    if design_guide and design_guide.get("filename"):
        cites = design_guide.get("citations") or []
        cite_txt = "\n".join(f"- {c}" for c in cites[:8]) or "(no citation anchors)"
        guide_block = (
            f"Design guide bible: {design_guide.get('filename')}\n"
            f"Excerpt:\n{(design_guide.get('excerpt') or '')[:2500]}\n"
            f"Citation anchors:\n{cite_txt}"
        )
    user = (
        f"LLMHub model in use: {model or 'default'}\n"
        f"Factor: {factor} ({meta['label']})\n\n"
        f"--- Design guide ---\n{guide_block}\n--- end design guide ---\n\n"
        f"--- Repository digest ---\n{repo_digest}\n--- end digest ---\n\n"
        "Analyze this factor and return the JSON now."
    )
    return system, user


def build_code_analysis_supervisor_prompts(
    *,
    factor_results: list[dict[str, Any]],
    design_guide: dict[str, Any] | None = None,
    model: str | None = None,
    static_seed: dict[str, Any] | None = None,
) -> tuple[str, str]:
    import json

    guide_name = (design_guide or {}).get("filename") or "none"
    user = (
        f"Model: {model or 'default'}\n"
        f"Design guide: {guide_name}\n\n"
        f"Sub-agent findings JSON:\n{json.dumps(factor_results, ensure_ascii=False)[:48000]}\n\n"
    )
    if static_seed:
        user += (
            "Static heuristic seed (optional corroboration, do not copy blindly):\n"
            f"{json.dumps(static_seed, ensure_ascii=False)[:8000]}\n\n"
        )
    user += "Supervise, score, and return the consolidated dashboard JSON now."
    return CODE_ANALYSIS_SUPERVISOR_SYSTEM, user
