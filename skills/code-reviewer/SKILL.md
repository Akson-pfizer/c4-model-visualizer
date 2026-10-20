---
name: code-reviewer
description: Automated code quality, simplification (/simplify), and maintainability review skill adapted with ui-experience's SonarQube Code-Quality Gate (~75 findings distilled) and ui-ux-master's dual-audience Business/Tech reporting.
category: 2026-must-have
origin: "10 Must-Have Skills for Claude (and Any Coding Agent) in 2026 (#3)"
install_command: "npx skills add anthropics/claude-code --skill simplify"
slash_command: "/code-reviewer"
applicable_agents:
  - c4-manager
  - c4-supervisor
  - subagent-context
  - subagent-container
  - subagent-component
  - subagent-code
  - c4-doc-agent
---

# Skill 03: Code Reviewer & Simplify (`code-reviewer`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose & Problem Solved
Transforms first-draft agent code into maintainable, production-ready code before presenting it to the user. Enforces single-responsibility functions, DRY utility extraction, strict typing, and preemptive SonarQube compliance.

## 2. `ui-experience` Preemptive SonarQube Code-Quality Gate
Every file written or reviewed by any agent must pass these write-time rules distilled from `ui-experience/references/code-quality-gate.md`:
1. **No Nested Ternaries (`S3358`)**: Extract into a lookup map (`STATUS_LABELS[status] ?? 'Unknown'`) or helper function.
2. **No Nested Template Literals (`S4624`)**: Compute inner strings into descriptive variables first.
3. **Native Semantic HTML Elements (`S6819`, `S6847`)**:
   - Use `<dialog>` instead of `<div role="dialog">`.
   - Use `<output>` instead of `<div role="status">`.
   - Use `<button type="button">` for all clickable triggers; never attach click handlers to non-interactive `<div>` or `<span>` elements.
4. **Cognitive Complexity `<= 15` (`S3776`) & Function Length `<= 30` Lines**: Extract render branches into atomic subcomponents and complex conditionals into pure helper functions.
5. **Component Budget `<= 400` Lines (`Lesson L3`)**: Split monolith files into `ui/` primitives and feature subcomponents before adding new features.
6. **Friendly User-Facing Error Helper (`Lesson L4`)**: Never render raw `err.message` or stack traces in the UI; translate HTTP/network errors into plain language with a constructive recovery action (Nielsen Heuristic #9).
7. **Modern Idioms**: Use `.at(-1)` (`S7755`), `replaceAll()` (`S7781`), `Set.has()` (`S7776`), and optional chaining `a?.b` (`S6582`).

## 3. `ui-ux-master` Finding & Remediation Format
Every code review finding is reported with:
- **Issue**: Plain-language summary of the maintainability or UX defect.
- **Evidence**: Exact `file:line` reference.
- **Standard Violated**: SonarQube rule ID + Nielsen heuristic / Atomic Design reference.
- **Fix**: Concrete refactoring applied or recommended.
- **Effort & Impact**: `S` / `M` / `L` effort with Business (rework cost avoidance per Boehm's curve) and Tech translation.
