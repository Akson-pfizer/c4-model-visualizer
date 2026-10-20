---
name: confluence-export
description: Packages C4 architecture diagrams (.mmd, .svg, .png) and ui-ux-master plain-language reports (ux_analysis_report.md, 11-section scorecard, Quick-Wins roadmap) for Confluence publishing.
category: reusable
origin: "C4 Core & UI/UX Architecture Suite"
install_command: "Built-in (POST /api/docs/generate)"
slash_command: "/confluence-export"
applicable_agents:
  - c4-doc-agent
  - c4-manager
---

# Skill 17: Confluence & UX Report Packager (`confluence-export`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose
Bundles all generated Mermaid source files (`.mmd`), vector graphics (`.svg`), Confluence-ready raster images (`.png`), and `ui-ux-master` plain-language audit reports into a cohesive documentation package.

## 2. `ui-ux-master` & `ui-experience` Reporting Standards
1. **Executive Summary (`<= 10` Sentences)**: Verdict-first 2-minute read (`Lesson L10`) readable by non-technical stakeholders without jargon.
2. **One-Clause Technical Definitions**: Every technical acronym (`INP`, `LCP`, `CLS`, `AST`, `WCAG POUR`, `SUS`) is explained in a single plain-language clause on first use.
3. **Prioritized Recommendations Roadmap**: Ranked by `Severity (0-4) x Effort (S/M/L)`, placing **Quick Wins (`Severity >= 3`, `Effort = S`)** at the top of the sprint backlog.
