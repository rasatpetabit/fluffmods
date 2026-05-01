---
id: protect-user-work
label: Treat existing uncommitted changes as user-owned
version: 1.0.0
updated_on: 2026-04-30
---
## User-Owned Worktree Changes

Treat existing uncommitted changes as user-owned. Do not revert, overwrite, reformat, or "clean up" unrelated changes unless the user explicitly asks for that operation.

When unrelated dirty files are present, work around them and keep the final report scoped to the files intentionally changed.
