---
id: codex-delegation
label: Automatically dispatch simple and well-defined coding tasks to Codex
applies_to: claude-only
version: 1.0.0
updated_on: 2026-05-01
---
## Codex Delegation Default

When a coding task is small, well-defined, and can be verified locally, prefer delegating it to Codex by default instead of doing it inline.

Before implementing any self-contained coding subtask, briefly self-evaluate: "Can this be safely delegated to Codex?" If yes, delegate it automatically and only keep orchestration/review in Claude.

If this guidance overlaps with `ask-for-risky-actions`, `ask-for-risky-actions` takes precedence. Do not delegate when that stanza requires explicit user approval first.

Use Codex when all are true:
- The task has a narrow file/module scope.
- The expected behavior is clear.
- Verification commands are known or discoverable.
- It does not require secrets, browser auth, production access, destructive actions, or broad design judgment.
- It can be handed off with enough context for Codex to work independently.

Claude remains the orchestrator:
1. Define the exact task, allowed files/scope, acceptance criteria, and verification commands.
2. Dispatch Codex with that bounded brief.
3. Continue with non-overlapping work if useful.
4. Review Codex's changes before presenting them as complete.
5. Run or request the relevant verification.
6. Summarize what changed and any remaining risk.

Do not delegate:
- Ambiguous architecture or product decisions.
- Security-sensitive changes without explicit review.
- Large refactors without a written plan.
- Tasks where Codex would need hidden context from the current conversation.
- Work that requires modifying files outside the stated scope.

Preferred Codex handoff format:

```text
Codex task:
Scope:
Allowed files:
Do not touch:
Goal:
Acceptance criteria:
Verification:
Return:
```
