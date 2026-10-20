---
name: excalidraw-diagram
description: Visual architecture diagram generator ("diagrams that argue, not display") with visual self-validation, adapted with ui-ux-master (Gestalt proximity, cognitive load cap <=15 elements, Atlassian design tokens, WCAG AA contrast) and ui-experience (inline modal preview, zero overlap).
category: 2026-must-have
origin: "10 Must-Have Skills for Claude (and Any Coding Agent) in 2026 (#10)"
install_command: "npx skills add https://github.com/coleam00/excalidraw-diagram-skill --skill excalidraw-diagram"
slash_command: "/excalidraw-diagram"
applicable_agents:
  - c4-supervisor
  - subagent-context
  - subagent-container
  - subagent-component
  - subagent-code
  - c4-doc-agent
---

# Skill 10: Excalidraw Diagram Generator (`excalidraw-diagram`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose & Problem Solved
Generates architecture diagrams that *argue visually* rather than dumping uniform card grids. Maps conceptual topology (fan-out orchestration, sequential pipelines, convergence gates) to visual geometry with inline code/JSON evidence and automated visual self-validation.

## 2. `ui-ux-master` Visual & Perceptual Standards
1. **Gestalt Proximity & Similarity (`nngroup-gestalt-proximity.md`)**:
   - Group related containers and components inside explicit boundary frames (`c4Boundary`).
   - Use consistent shape/color tokens (`--blue-50`, `--blue-700`, `--surface`) so identical element kinds share visual signifiers.
2. **Cognitive Load Cap (`<= 15` Elements per Diagram)**:
   - Enforce C4 density compliance (`nodes + boundaries <= 15` per layer) so diagrams remain readable in under 30 seconds.
3. **WCAG 2.2 AA Contrast**:
   - Verify `>= 4.5:1` text contrast on all node labels and edge annotations before exporting `.svg` and `.png`.

## 3. `ui-experience` Self-Validation & Modal Preview
- **Visual Self-Validation Loop**: Render every diagram to `.svg` and `.png`, inspect for overlapping labels, dangling edges, or count mismatches, and auto-repair before completion.
- **Principle 3 — In-Place Modal Inspection**: Preview generated diagrams inside a native `<dialog>` modal (`~90%` screen, `✕` close button) rather than opening external browser tabs.
