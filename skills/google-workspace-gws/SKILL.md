---
name: google-workspace-gws
description: Google Workspace CLI (gws) & MCP automation across 50+ APIs (Docs, Sheets, Drive, Gmail, Calendar) adapted with ui-ux-master (dual-audience executive scorecards, plain-language reports) and ui-experience (2-minute verdict-first review artifacts).
category: 2026-must-have
origin: "10 Must-Have Skills for Claude (and Any Coding Agent) in 2026 (#5)"
install_command: "npx skills add https://github.com/googleworkspace/cli"
slash_command: "/gws"
applicable_agents:
  - c4-manager
  - c4-doc-agent
---

# Skill 05: Google Workspace Automation (`google-workspace-gws`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose & Problem Solved
Unifies 50+ Google Workspace APIs via Google's Discovery Service (`@googleworkspace/cli` + MCP server) so agents can publish architecture reviews to Google Docs, export UX metric scorecards to Sheets, and schedule design reviews on Calendar.

## 2. `ui-ux-master` Report & Scorecard Formatting Rules
When exporting C4 or UI/UX analysis artifacts to Google Docs or Sheets:
1. **Executive Summary First (`<= 10` Sentences)**: Open every document with a standalone plain-language summary framing business value (McKinsey Design Index / Boehm's cost-of-change curve).
2. **Dual-Audience Metric Rows**: Every row in a exported Google Sheet scorecard must include:
   - `Metric Name`
   - `Value` tagged `[measured]` or `[projected]`
   - `What it means for the business` (time, money, compliance risk)
   - `What it means for engineering` (concrete `file:line` remediation)
3. **Prioritized Roadmap**: Sort findings by Quick Wins (`Severity >= 3`, `Effort = S`) first.

## 3. `ui-experience` Operational Guardrails
- **Lesson L10 — 2-Minute Verdict-First Summaries**: Structure stakeholder emails and Chat updates with the overall verdict on line 1, systemic issues second, and `HIGH`/`MED`/`LOW` screen gaps third.
- **Error Prevention (Nielsen Heuristic #5)**: Confirm target folder/document permissions before mutating shared Workspace resources.
