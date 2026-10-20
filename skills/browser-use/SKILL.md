---
name: browser-use
description: Live web and headless browser automation skill adapted with ui-ux-master (live Core Web Vitals measurement, funnel drop-off verification, WCAG keyboard/focus audit) and ui-experience (L6 reproduce bugs live in browser before fixing, L1 verify input focus stability during typing).
category: 2026-must-have
origin: "10 Must-Have Skills for Claude (and Any Coding Agent) in 2026 (#2)"
install_command: "npx skills add https://github.com/browser-use/browser-use --skill browser-use"
slash_command: "/browser-use"
applicable_agents:
  - c4-manager
  - c4-supervisor
  - c4-doc-agent
---

# Skill 02: Browser Use (`browser-use`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose & Problem Solved
Eliminates agent blindness to the live rendered DOM. Connects agents to a live headless browser to navigate URLs, interact with controls, fill forms, capture screenshots, and verify end-to-end UX behavior.

## 2. `ui-experience` Live Verification Rules
1. **Lesson L6 — Reproduce Live Before Fixing**: Never guess at a UI bug from static source code alone. Open the live URL, reproduce the issue, record the root cause, and verify the fix in the browser.
2. **Lesson L1 — Focus-Preserving Input Test**: Type multi-character strings into every search/combobox `<input>` and assert `document.activeElement` remains the input across keystrokes (preventing DOM subtree re-render bugs).
3. **Lesson L5 — Cross-Cutting Checklist Walk**: Navigate through every tab (`Visualizer`, `Developer`, `Code Analysis`) and verify that global source state, filter selections, and modal behaviors remain consistent across all tabs.

## 3. `ui-ux-master` Empirical Measurement Protocol
- Upgrades static `[projected]` metrics to `[measured]` when executed against the live running server:
  - **Core Web Vitals (`[measured]`)**: Capture Largest Contentful Paint (LCP `< 2.5s`), Interaction to Next Paint (INP `< 200ms`), and Cumulative Layout Shift (CLS `< 0.1`).
  - **Funnel & Ergonomics (`[measured]`)**: Count actual clicks, keystrokes, and scroll depth required to complete the primary user workflow.
  - **Accessibility Audit (`[measured]`)**: Verify computed contrast ratios, visible `:focus-visible` outlines, and fold placement on desktop and mobile viewports (`860px` breakpoint).
- Every finding reported from browser runs follows: **Issue -> Evidence (`file:line` + screenshot) -> Standard violated -> Fix -> Effort (`S`/`M`/`L`) -> Expected impact**.
