---
name: remotion
description: React/programmatic video walkthrough & animated architecture demo generator adapted with ui-ux-master (cognitive load pacing, WCAG captioning/contrast, Gestalt motion continuity) and ui-experience (wireframe-to-implementation storytelling).
category: 2026-must-have
origin: "10 Must-Have Skills for Claude (and Any Coding Agent) in 2026 (#4)"
install_command: "npx skills add remotion/agent-skills"
slash_command: "/remotion"
applicable_agents:
  - c4-doc-agent
  - c4-supervisor
---

# Skill 04: Remotion Programmatic Video (`remotion`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose & Problem Solved
Translates C4 architecture flows, release notes, and UI walkthroughs into deterministic, frame-accurate programmatic videos (`useCurrentFrame()`, `interpolate()`, `spring()`) without leaving the codebase.

## 2. `ui-ux-master` Perceptual & Accessibility Rules for Motion
1. **Cognitive Load & Pacing (`nngroup-minimize-cognitive-load.md`)**:
   - Reveal at most one C4 layer transition (`Context -> Container -> Component -> Code`) per 90-frame (3-second) scene so viewers are never overwhelmed by simultaneous motion.
2. **Gestalt Continuity & Proximity**:
   - Animate connected nodes along their actual directed edge paths so visual motion reinforces architectural data flow.
3. **WCAG 2.2 AA POUR for Media**:
   - Enforce `>= 4.5:1` text contrast on all video overlays using the project's soft white & Pfizer blue design tokens (`#fbfcfe`, `#1d4ed8`, `#1e3a6a`).
   - Avoid rapid flashing (`< 3` flashes/sec) and include synchronized caption tracks for every narration beat.

## 3. `ui-experience` Workflow Alignment
- **Data-First Storyboarding**: Start video demos on the most-used view with realistic, pairwise-distinct node IDs (`Lesson L2`), never on an empty loading screen.
- **Clean Component Decomposition**: Keep each Remotion scene composition under 150 lines with zero nested ternaries (`S3358`).
