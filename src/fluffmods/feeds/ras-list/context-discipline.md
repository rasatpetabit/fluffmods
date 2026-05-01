---
id: context-discipline
label: Keep context usage disciplined in large ongoing work
version: 1.0.0
updated_on: 2026-05-01
---
## Context Discipline

Treat context as scarce. Prefer targeted search and line-range reads over opening whole files. Do not read generated files, lockfiles, vendored code, logs, build outputs, or session transcripts unless directly relevant. Reuse facts already gathered instead of repeatedly re-reading unchanged files.

Keep the main thread focused on decisions, integration, edits, and verification. For long tasks, maintain a short working summary: goal, files inspected, files changed, decisions, verification, blockers, and next step.

Use subagents only for bounded, parallel work with clear scope. Give each subagent exact files, directories, symbols, or commands to inspect, and ask for concise findings with file paths, line numbers, commands run, and blockers. Do not ask subagents to paste large file contents or do broad repo-wide exploration. The main thread owns final integration and verification.

When context gets high, stop broad exploration, summarize state, write durable handoff notes when a repo surface exists, and recommend compacting or starting a fresh session.
