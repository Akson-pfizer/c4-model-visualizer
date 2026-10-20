---
name: draw-diagram
description: Synthesizes C4 JSON graphs, 4-tier Hierarchy Trees, and Confluence-ready Mermaid (.mmd), SVG (.svg), and PNG (.png) diagrams adapted with ui-ux-master (Gestalt grouping, <=15 node cognitive load cap, WCAG AA contrast) and ui-experience (layer/tree view toggle state preservation).
category: core
origin: "C4 Core & UI/UX Architecture Suite"
install_command: "Built-in (app/doc_agent.py & app/png_renderer.py)"
slash_command: "/draw-diagram"
applicable_agents:
  - c4-supervisor
  - subagent-context
  - subagent-container
  - subagent-component
  - subagent-code
  - c4-doc-agent
---

# Skill 12: Draw C4 & Mermaid Diagrams (`draw-diagram`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose
Generates interactive SvelteFlow C4 layer graphs, 4-tier Hierarchy Trees, and static `.mmd`, `.svg`, and `.png` diagrams for Confluence.

## 2. `ui-ux-master` & `ui-experience` Diagram Rules
1. **Minimize Extraneous Cognitive Load**: Cap every diagram at `<= 15` nodes + boundaries per layer (`[measured]` C4 density compliance).
2. **Gestalt Proximity & Affordances**: Use explicit `c4Boundary` containers, distinct technology badges (`Principle 13`), and high-contrast directional edges (`>= 4.5:1` label contrast).
3. **State Survival Across Toggles (`Principle 12`)**: Switching between `Layer` and `Tree` views or across `Context -> Container -> Component -> Code` preserves the active repository model without resetting filters.
