# Agent Skills Catalog (`c4-model-visualizer/skills/`)

All **17 Agent Skills** in this directory follow the portable `SKILL.md` format and have been adapted to enforce the UI/UX engineering standards from:
- **`~/.claude/skills/ui-ux-master`**: Nielsen's 10 usability heuristics (NN/g 0–4 severity scale), WCAG 2.2 AA / POUR contrast & keyboard operability, Cognitive Load minimization, Fitts's Law, Gestalt proximity, Brad Frost Atomic Design & Atlassian Design Tokens, McKinsey Design Index / Boehm Cost-of-Change framing, strict `[measured]` vs `[projected]` metric tagging, and Dual-Audience (**Business** + **Tech**) translations.
- **`~/.claude/skills/ui-experience`**: 6-Phase UI workflow (Inventory -> Frozen `preview.html` Wireframe -> Screen-by-Screen Implementation with live `cross-cutting-checklist` -> Ergonomics Audit -> 2-Minute Verdict-First Review -> SonarQube Code-Quality Gate), tabs-not-pages, two docked collapsible sidebars, native `<dialog>` modals (~90% screen, `✕` close button), hybrid combobox search, data-first defaults, `<400` LOC component budget (`L3`), focus-safe inputs (`L1`), pairwise-distinct mock data (`L2`), and friendly user error helpers (`L4`).

---

## Part A — 10 Must-Have Coding Agent Skills (2026 Guide by `@unicodeveloper`)

Reference: [10 Must-Have Skills for Claude (and Any Coding Agent) in 2026](https://medium.com/@unicodeveloper/10-must-have-skills-for-claude-and-any-coding-agent-in-2026-b5451b013051)

| # | Skill ID | Name | Slash Command | Install Command | UI/UX Master & UI-Experience Adaptation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `frontend-design` | **Frontend Design** | `/frontend-design` | `npx skills add anthropics/claude-code --skill frontend-design` | Atomic design tokens (`--blue-700`, `--surface`), frozen wireframe ground truth, docked collapsible sidebars, native `<dialog>`, `<400` LOC budget. |
| 2 | `browser-use` | **Browser Use** | `/browser-use` | `npx skills add https://github.com/browser-use/browser-use --skill browser-use` | Live bug reproduction (`L6`), input focus-retention test (`L1`), empirical `[measured]` Core Web Vitals & WCAG AA verification. |
| 3 | `code-reviewer` | **Code Reviewer (Simplify)** | `/code-reviewer` | `npx skills add anthropics/claude-code --skill simplify` | Preemptive SonarQube gate: zero nested ternaries (`S3358`), cognitive complexity `<= 15` (`S3776`), native `<dialog>`/`<output>`/`<button>` (`S6819`), friendly error helper (`L4`). |
| 4 | `remotion` | **Remotion Video** | `/remotion` | `npx skills add remotion/agent-skills` | Cognitive load pacing (1 C4 layer per 3s scene), Gestalt motion continuity, WCAG AA overlay contrast (`>= 4.5:1`). |
| 5 | `google-workspace-gws` | **Google Workspace (GWS)** | `/gws` | `npx skills add https://github.com/googleworkspace/cli` | Exports 2-minute verdict-first summaries (`L10`) and dual-audience (`Business` + `Tech`) scorecards to Docs/Sheets. |
| 6 | `valyu` | **Valyu Specialized Data** | `/valyu` | `npx skills add https://github.com/valyuai/skills --skill valyu-best-practices` | Reference reliability verification (`05-reference-reliability-assessment.md`), `[measured]` vs `[projected]` provenance badges, modal citation previews. |
| 7 | `antigravity-awesome-skills` | **Antigravity Awesome Skills** | `/antigravity` | `npx antigravity-awesome-skills --cursor` | Role bundles (`Web Wizard`, `Security Engineer`, `Essentials`) mapped to Phase 0–6 spec-driven & SonarQube gates. |
| 8 | `planetscale` | **PlanetScale Database Skills** | `/planetscale` | `npx skills add planetscale/agent-skill` | Explicit kind/status columns (`Principle 13`), pairwise-distinct IDs (`L2`), data-first query defaults (`Principle 9`), composite indexes for `<200ms` INP. |
| 9 | `shannon` | **Shannon AI Pentester** | `/shannon` | `npx skills add unicodeveloper/shannon` | OWASP white-box audit + UI error sanitization (`L4`, never expose raw `err.message`), strict Local vs GitHub path validation (`SourceBar`). |
| 10 | `excalidraw-diagram` | **Excalidraw Diagram Generator** | `/excalidraw-diagram` | `npx skills add https://github.com/coleam00/excalidraw-diagram-skill --skill excalidraw-diagram` | "Diagrams that argue, not display", C4 density cap (`<= 15` nodes), Gestalt boundary grouping, visual self-validation & native `<dialog>` preview. |

---

## Part B — 7 Core C4 Architecture & Documentation Skills

| # | Skill ID | Name | Slash Command | UI/UX Master & UI-Experience Adaptation |
| :--- | :--- | :--- | :--- | :--- |
| 11 | `read-code` | **Read the Code & AST Inventory** | `/read-code` | Scans Python AST & Svelte 5 files + inventories component LOC budgets (`L3`), design tokens, semantic HTML, and SonarQube rules. |
| 12 | `draw-diagram` | **Draw C4 & Mermaid Diagrams** | `/draw-diagram` | Enforces `<= 15` elements/layer cognitive load cap, WCAG AA contrast, and state preservation across `Layer`/`Tree` toggles (`Principle 12`). |
| 13 | `execute-sandbox` | **Execute App in Sandbox** | `/execute-sandbox` | Runs isolated sandbox verification with pairwise-distinct dummy data (`L2`) and reports `[measured]` latency & traceability telemetry. |
| 14 | `follow-workflows` | **Follow Workflows & SOPs** | `/follow-workflows` | Unifies the 7-agent C4 pipeline with the 6-phase `ui-experience` workflow and live `cross-cutting-checklist` (`L5`). |
| 15 | `evaluate-metrics` | **Evaluate Architecture & UX Metrics** | `/evaluate-metrics` | Computes C4 quality scores + the 10-section `ui-ux-master` checklist with `[measured]`/`[projected]` tags and Business/Tech translations. |
| 16 | `validate-repair` | **Validate & Self-Repair** | `/validate-repair` | Repairs dangling C4 edges/parents and audits semantic HTML (`<dialog>`, `<output>`, `<button>`) and SonarQube compliance. |
| 17 | `confluence-export` | **Confluence & UX Report Packager** | `/confluence-export` | Produces plain-language `ux_analysis_report.md`, `.mmd`, `.svg`, and `.png` bundles with Quick Wins (`Severity >= 3`, `Effort = S`) ranked first. |
