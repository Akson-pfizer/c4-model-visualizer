---
name: validate-repair
description: Validates Pydantic schemas, C4 parentNodeId links, Mermaid syntax, and UI/UX accessibility & SonarQube write-time rules with automated self-healing repair.
category: reusable
origin: "C4 Core & UI/UX Architecture Suite"
install_command: "Built-in (app/c4_service.py & app/doc_agent.py)"
slash_command: "/validate-repair"
applicable_agents:
  - c4-supervisor
  - subagent-context
  - subagent-container
  - subagent-component
  - subagent-code
  - c4-doc-agent
---

# Skill 16: Schema, Diagram & UI/UX Validation & Self-Repair (`validate-repair`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose
Enforces zero-defect outputs across C4 JSON layers, Mermaid diagrams, and UI components through automated validation and self-healing repair loops.

## 2. Integrated Validation & Repair Checks
1. **C4 & Mermaid Structural Integrity**:
   - Prunes dangling edges whose `source` or `target` node ID is missing.
   - Auto-links orphaned child nodes (`Container`, `Component`, `Code`) to valid `parentNodeId` roots.
2. **`ui-experience` Code-Quality & Accessibility Gate**:
   - Verifies native `<dialog>` and `<output>` usage (`S6819`), keyboard parity on interactive elements (`S6847`), zero nested ternaries (`S3358`), and friendly error formatting (`Lesson L4`).
