---
name: follow-workflows
description: Enforces the 6-phase ui-experience workflow (Inventory -> Frozen Wireframe -> Screen-by-Screen Implementation -> UX Ergonomics Audit -> 2-Min Verdict Review -> SonarQube Gate) alongside the C4 multi-agent pipeline.
category: core
origin: "C4 Core & UI/UX Architecture Suite"
install_command: "Built-in (app/agents.py & app/doc_agent.py)"
slash_command: "/follow-workflows"
applicable_agents:
  - c4-manager
  - c4-supervisor
  - subagent-context
  - subagent-container
  - subagent-component
  - subagent-code
  - c4-doc-agent
---

# Skill 14: Follow Multi-Agent & UI/UX Workflows (`follow-workflows`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose
Orchestrates both the **C4 Multi-Agent Extraction Pipeline** (`Manager -> Supervisor -> Context -> Container -> Component -> Code -> Doc Agent`) and the **`ui-experience` 6-Phase UI Engineering Workflow**.

## 2. Integrated Workflow Phases
1. **Phase 0**: Inventory repository symbols, screens, forms, and user tasks (`read-code`).
2. **Phase 1**: Establish frozen architecture & wireframe contracts (`draw-diagram`).
3. **Phase 2**: Execute layer-by-layer extraction and screen-by-screen implementation while checking the live `cross-cutting-checklist` (`Lesson L5`).
4. **Phase 3**: Run ergonomics & cognitive load audit (click counts, Fitts's Law target proximity, data-first defaults).
5. **Phase 4**: Generate a 2-minute verdict-first review (`Lesson L10`) and `ui-ux-master` scorecard.
6. **Phase 6**: Enforce the SonarQube write-time gate (`code-reviewer` + `validate-repair`).
