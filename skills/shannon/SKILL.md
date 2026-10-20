---
name: shannon
description: Autonomous white-box AI security & OWASP pentesting skill (Injection, XSS, SSRF, AuthN, AuthZ) adapted with ui-experience (L4 safe error sanitization, SourceBar strict path/URL validation) and ui-ux-master (Nielsen Heuristic #5 Error Prevention & severity 0-4 risk rating).
category: 2026-must-have
origin: "10 Must-Have Skills for Claude (and Any Coding Agent) in 2026 (#9)"
install_command: "npx skills add unicodeveloper/shannon"
slash_command: "/shannon"
applicable_agents:
  - c4-manager
  - c4-supervisor
  - subagent-container
  - subagent-component
  - c4-doc-agent
---

# Skill 09: Shannon Autonomous AI Pentester (`shannon`) — Adapted for `ui-ux-master` & `ui-experience`

## 1. Purpose & Problem Solved
Performs white-box static and dynamic security analysis across 5 OWASP categories (Injection, XSS, SSRF, Broken Authentication, Broken Authorization) with a "no exploit / no concrete evidence, no report" policy and strict authorization gates.

## 2. `ui-experience` Security & UX Guardrails
1. **Lesson L4 — Safe Error Sanitization**:
   - Never expose raw stack traces, internal filesystem paths, or raw `err.message` payloads to the browser DOM. Use the shared friendly error translator.
2. **Strict Input Boundary Validation (`SourceBar.svelte` & `repo_scanner.py`)**:
   - Enforce client-side and server-side validation separating `Local` filesystem paths from `Github` `https://github.com/<owner>/<repo>` URLs to prevent SSRF, command injection, and path traversal.
3. **Avoid-List & Container Isolation**:
   - Run dynamic verification strictly inside isolated sandboxes (`execute-sandbox`) or Docker containers; never target production systems.

## 3. `ui-ux-master` Security-Usability Audit Format
- Maps every security or input-validation flaw onto the **NN/g 0–4 Severity Scale** (`4 = Catastrophic / compliance or exploit risk`, `3 = Major`):
  - **Issue -> Evidence (`file:line`) -> Standard violated (OWASP + Nielsen #5 Error Prevention) -> Fix -> Effort (`S`/`M`/`L`) -> Expected impact (Business risk reduction + Tech patch)**.
