---
name: valyu
description: Real-time web search and 36+ specialized authoritative data sources (SEC filings, PubMed, ChEMBL, ClinicalTrials, benchmarks) adapted with ui-ux-master (strict reference reliability assessment, [measured] vs [projected] tagging, inline citation trails).
category: 2026-must-have
origin: "10 Must-Have Skills for Claude (and Any Coding Agent) in 2026 (#6)"
install_command: "npx skills add https://github.com/valyuai/skills --skill valyu-best-practices"
slash_command: "/valyu"
applicable_agents:
  - c4-manager
  - c4-supervisor
  - c4-doc-agent
---

# Skill 06: Valyu Specialized Data & Grounded Search (`valyu`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose & Problem Solved
Connects coding agents to 36+ authoritative domain databases (SEC filings, PubMed, ChEMBL, clinical trials, technical standards) so architectural and UX claims are grounded in verifiable primary evidence rather than hallucinated numbers.

## 2. `ui-ux-master` Evidence & Reliability Discipline
1. **Primary Source Citation (`05-reference-reliability-assessment.md`)**:
   - Every benchmark, regulatory claim, or UX heuristic cited in reports or UI tooltips must link to its primary source document.
   - Distinguish empirical measurements (`[measured]`) from literature projections (`[projected]`).
2. **Targeted Source Filtering**:
   - Always pass explicit `included_sources` rather than broad uncurated queries to minimize noise and cognitive load.

## 3. `ui-experience` UI Presentation Rules
- **Inline Citation Badges (Principle 13)**: Surface source provenance as compact, accessible `<output>` or badge chips next to metrics.
- **Modals, Not External Tab Traps (Principle 3)**: Preview cited evidence excerpts inside a native `<dialog>` modal rather than forcing users away from their active analysis workspace.
- **Friendly Fallback (Lesson L4)**: When an external data API is unreachable, fall back gracefully to the local verified standards archive (`ddapp` / local repository inventory) with a clear status indicator.
