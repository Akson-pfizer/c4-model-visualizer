---
name: read-code
description: Scans local or cloned GitHub repositories, extracts Python AST symbols and Svelte/ES components, and inventories UI/UX artifacts (screens, forms, tokens, ARIA/native elements) per ui-ux-master §3 and ui-experience Phase 0.
category: core
origin: "C4 Core & UI/UX Architecture Suite"
install_command: "Built-in (app/skills_registry.py :: skill_read_code_summary)"
slash_command: "/read-code"
applicable_agents:
  - c4-manager
  - c4-supervisor
  - subagent-context
  - subagent-container
  - subagent-component
  - subagent-code
  - c4-doc-agent
---

# Skill 11: Read the Code & UI/AST Inventory (`read-code`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose
Reads repository source trees to extract both **C4 architectural symbols** (Python AST classes/functions, Svelte 5 components, Docker Compose services) and **`ui-ux-master` / `ui-experience` static code health signals**.

## 2. `ui-ux-master` §3 & `ui-experience` Phase 0 Inventory Checklist
When scanning a codebase, `read-code` inventories:
1. **File & Component Size Budget (`Lesson L3`)**: Measures line counts per file and flags any component exceeding the 400-line atomic design budget.
2. **SonarQube Write-Time Gate (`code-quality-gate.md`)**: Scans for nested ternaries (`S3358`), nested template literals (`S4624`), non-interactive click handlers (`S6847`), and raw `err.message` rendering (`Lesson L4`).
3. **Design Tokens vs Hard-Coded Styles**: Counts CSS custom property usage (`var(--*)`) vs hard-coded hex colors.
4. **Accessibility & Semantic HTML (`WCAG 2.2 AA`)**: Checks for native `<dialog>`, `<output>`, `<button>`, `<label for="...">`, and keyboard navigation handlers.
