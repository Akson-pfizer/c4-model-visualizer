---
name: execute-sandbox
description: Executes the multi-agent pipeline in an isolated temporary sandbox with pairwise-distinct dummy data (ui-experience Lesson L2) and captures empirical [measured] latency and traceability metrics (ui-ux-master §5).
category: core
origin: "C4 Core & UI/UX Architecture Suite"
install_command: "Built-in (POST /api/sandbox/run)"
slash_command: "/execute-sandbox"
applicable_agents:
  - c4-manager
  - c4-supervisor
  - c4-doc-agent
---

# Skill 13: Execute App in Sandbox with Dummy Data (`execute-sandbox`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose
Spins up an isolated temporary directory (`tempfile.TemporaryDirectory`), populates realistic multi-container dummy code, runs the 7-agent pipeline, and verifies 100% parent-child traceability.

## 2. `ui-experience` & `ui-ux-master` Sandbox Rules
1. **Lesson L2 — Pairwise-Distinct Dummy Data**: Synthetic nodes, components, and IDs must never share uniform prefixes that mask search/filter bugs.
2. **Honest Metric Tagging (`ui-ux-master` §5)**: Sandbox execution times (`execution_time_ms`), node counts, and traceability percentages are tagged `[measured]` because they are derived from live in-process execution.
3. **Lesson L4 — Resilient Error Handling**: Any sandbox assertion failure returns a structured diagnostic report with a concrete fix rather than crashing the UI.
