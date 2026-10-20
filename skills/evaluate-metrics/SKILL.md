---
name: evaluate-metrics
description: Computes quantitative C4 architecture metrics AND the 10-section ui-ux-master evaluation checklist (strictly tagging [measured] vs [projected] with Business and Tech translations for every metric).
category: reusable
origin: "C4 Core & UI/UX Architecture Suite"
install_command: "Built-in (app/skills_registry.py :: skill_compute_evaluation_metrics)"
slash_command: "/evaluate-metrics"
applicable_agents:
  - c4-supervisor
  - c4-doc-agent
---

# Skill 15: Architecture & UI/UX Evaluation Metrics (`evaluate-metrics`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose
Computes both **C4 Structural Quality Metrics** (Traceability 35%, Edge Integrity 30%, C4 Density $\le 15$ 25%, Schema Conformance 10%) and the **`ui-ux-master` 10-Section UX & Code Health Scorecard**.

## 2. `ui-ux-master` Hard Rules for Metric Honesty
1. **Strict `[measured]` vs `[projected]` Tagging**:
   - Metrics computed directly from static code, ASTs, or sandbox runs (contrast ratios, component LOC, field counts, step counts, traceability %, edge integrity %) are tagged **`[measured]`**.
   - Metrics requiring live user traffic or human surveys (SUS score range, A/B test lift, session heatmaps) are tagged **`[projected]`** and paired with a 1-line measurement plan.
2. **Dual-Audience Translation (Mandatory)**:
   - Every metric carries three lines:
     1. **Value** (`[measured]` or `[projected]`)
     2. **Business**: What it means in time, revenue, conversion, or compliance risk (citing McKinsey Design Index / Boehm's Cost-of-Change Curve).
     3. **Tech**: Concrete code/architecture action with `file:line`.
