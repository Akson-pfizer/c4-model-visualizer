---
name: planetscale
description: Serverless database schema branching, index-aware query optimization, and data modeling skill adapted with ui-experience (L2 pairwise-distinct realistic mock data, Principle 13 explicit kind/status columns, Principle 9 data-first query defaults) and ui-ux-master (LCP/INP query latency budgets).
category: 2026-must-have
origin: "10 Must-Have Skills for Claude (and Any Coding Agent) in 2026 (#8)"
install_command: "npx skills add planetscale/agent-skill"
slash_command: "/planetscale"
applicable_agents:
  - subagent-container
  - subagent-component
  - subagent-code
  - c4-doc-agent
---

# Skill 08: PlanetScale Database & Schema Branching (`planetscale`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose & Problem Solved
Prevents unindexed queries (`SELECT *`), fragile schema migrations, and ambiguous UI data states by treating database schemas as branched, reviewable code with composite index verification.

## 2. `ui-experience` Data-to-UI Alignment Rules
1. **Principle 13 & Lesson L8 — Explicit Kind/Status Columns**:
   - If the UI requires a record type or status badge (e.g., `kind`, `layer`, `category`, `status`), add an explicit indexed column or schema field rather than leaving the UI to guess from unstructured text.
2. **Lesson L2 — Pairwise-Distinct Seed & Sandbox Data**:
   - Seed scripts and sandbox fixtures must use pairwise-distinct IDs without shared substrings so substring search and combobox filters visibly narrow results during testing.
3. **Principle 9 & 15 — Data-First Defaults & True Aggregation**:
   - Default list queries must return recent records immediately without requiring a filter gate.
   - "All" filter queries must compute real aggregates (`COUNT`, `SUM`, weighted averages) rather than simply omitting the `WHERE` clause.

## 3. `ui-ux-master` Performance & Reliability Translation
- **Query Latency -> Core Web Vitals (`INP < 200ms`, `LCP < 2.5s`)**:
  - Replace `SELECT *` with explicit projection columns and composite indexes (`INDEX idx_status_created (status, created_at)`) so filter toggles respond in `< 50ms` (`[measured]`).
- Every schema recommendation includes **Business** impact (infrastructure cost & user abandonment avoidance) and **Tech** remediation (`CREATE INDEX` / Pydantic model contract).
