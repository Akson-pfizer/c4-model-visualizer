---
name: frontend-design
description: Official Anthropic production-grade UI generation skill adapted with ui-ux-master (Nielsen's 10 heuristics, WCAG 2.2 AA POUR, Fitts's Law, Gestalt, Atomic Design tokens) and ui-experience (frozen preview.html wireframe, tabs-not-pages, docked collapsible sidebars, native dialog modals, <400 LOC component budget, and SonarQube write-time gate).
category: 2026-must-have
origin: "10 Must-Have Skills for Claude (and Any Coding Agent) in 2026 (#1)"
install_command: "npx skills add anthropics/claude-code --skill frontend-design"
slash_command: "/frontend-design"
applicable_agents:
  - c4-manager
  - c4-supervisor
  - subagent-container
  - subagent-component
  - subagent-code
  - c4-doc-agent
---

# Skill 01: Frontend Design (`frontend-design`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose & Problem Solved
Breaks LLM "distributional convergence" (generic layouts, arbitrary gradients, ungrounded component sprawl) by enforcing a rigorous, standards-backed design system before any frontend code is written. Adapted with `~/.claude/skills/ui-ux-master` and `~/.claude/skills/ui-experience`.

## 2. `ui-experience` Phased Workflow Integration
1. **Phase 0 — Inventory Before Designing**: Map core user workflows, screens, forms, and interactive targets. Identify the user's most frequent task so it becomes the default landing view.
2. **Phase 1 — Frozen Wireframe Ground Truth**: Build a self-contained `preview.html` wireframe first. Once signed off, freeze it as the immutable ground truth.
3. **Phase 2 — Atomic Decomposition (`<= 400` Lines/File)**:
   - Decompose into **Atoms** (tokens, buttons, badges, inputs) -> **Molecules** (hybrid combobox search, metric cards) -> **Organisms** (docked collapsible sidebars, native `<dialog>` modals) -> **Screens**.
   - Never allow a component file to exceed ~400 lines (`ui-experience` Lesson L3).
4. **Layout & Navigation Rules**:
   - **One Page, Tabs — Not Multiple Pages**: Keep users oriented and preserve filter/selection state across tab switches.
   - **Two Docked Collapsible Sidebars**: Left sidebar for content/search filters; right sidebar for attribute/facet inspection.
   - **Modals, Not New Tabs**: Use a single shared native `<dialog>` component (~90% viewport, visible `✕` close button) instead of opening external browser tabs.
   - **Matching Titles**: Page header title and browser `<title>` must be identical (`C4 modelling`).

## 3. `ui-ux-master` Standards & Evaluation Rubric
- **Nielsen's 10 Heuristics (0–4 NN/g Severity Scale)**:
  - Visibility of system status (`<output>` status pills, Pfizer wordmark loader).
  - Recognition over recall & minimalist design (data-first defaults, progressive disclosure).
- **WCAG 2.2 AA / POUR Compliance**:
  - Text contrast `>= 4.5:1`, UI component / large text contrast `>= 3.0:1`.
  - Interactive targets `>= 24x24px` (Fitts's Law proximity & sizing for primary CTAs).
  - Full keyboard parity (`ArrowLeft`/`ArrowRight`/`Home`/`End` on tablists, `Escape` on `<dialog>`).
- **Design Tokens**: All colors, shadows, radii, and typography must reference CSS custom properties (`--surface`, `--blue-700`, `--border`), never scattered hard-coded hex values.
- **SonarQube Write-Time Gate**: Zero nested ternaries (S3358), zero nested template literals (S4624), cognitive complexity `<= 15` (S3776).
