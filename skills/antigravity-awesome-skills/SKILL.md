---
name: antigravity-awesome-skills
description: Curated library of 1,234+ cross-agent skills (@brainstorming, @architecture, @debugging-strategies, @api-design-principles, @security-auditor, @lint-and-validate, @doc-coauthoring) adapted with ui-experience phased workflows and ui-ux-master standards.
category: 2026-must-have
origin: "10 Must-Have Skills for Claude (and Any Coding Agent) in 2026 (#7)"
install_command: "npx antigravity-awesome-skills --cursor"
slash_command: "/antigravity"
applicable_agents:
  - c4-manager
  - c4-supervisor
  - subagent-context
  - subagent-container
  - subagent-component
  - subagent-code
  - c4-doc-agent
---

# Skill 07: Antigravity Awesome Skills (`antigravity-awesome-skills`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose & Problem Solved
Provides role-based starter bundles (`Web Wizard`, `Security Engineer`, `Essentials`) from a curated catalog of 1,234+ portable `SKILL.md` playbooks (`@brainstorming`, `@architecture`, `@debugging-strategies`, `@api-design-principles`, `@security-auditor`, `@lint-and-validate`, `@create-pr`, `@doc-coauthoring`).

## 2. Role Bundles Adapted to `ui-experience` & `ui-ux-master`
1. **`@brainstorming` + `@architecture` (Phase 0 & Phase 1 Gate)**:
   - Enforces Spec-Driven Development (`01-ui-ux-design-principles.md`): define user workflows, component boundaries, and the frozen `preview.html` wireframe before writing implementation code (Boehm's 1-10-100 cost-of-change rule).
2. **`@debugging-strategies` (Lesson L6)**:
   - Reproduce bugs live first, isolate whether the failure is state/DOM destruction (`Lesson L1`) or mock data masking (`Lesson L2`), and document the root cause in writing.
3. **`@api-design-principles` (Lesson L4)**:
   - Ensure every FastAPI endpoint returns structured JSON error details that the frontend's shared error helper can translate into plain, helpful user messages.
4. **`@lint-and-validate` (Phase 6 Code-Quality Gate)**:
   - Enforce cognitive complexity `<= 15`, zero nested ternaries, semantic `<dialog>`/`<output>`/`<button>` markup, and `<= 400` lines per file.
5. **`@doc-coauthoring` (`ui-ux-master` Plain-Language Rule)**:
   - Explain every technical acronym in one clause on first use and pair every metric with Business and Engineering translations.
