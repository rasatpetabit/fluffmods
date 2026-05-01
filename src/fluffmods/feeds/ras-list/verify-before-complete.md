---
id: verify-before-complete
label: Require local verification before claiming implementation work is done
version: 1.0.0
updated_on: 2026-05-01
---
## Verification Before Completion

Before saying implementation work is complete, run the most relevant local verification commands when they are available and safe. Prefer the repository's own scripts, Makefile targets, package scripts, or documented commands over ad hoc checks.

Verification commands must not modify unrelated dirty files. If a verification path risks touching user-owned work, defer to `protect-user-work` and report the remaining risk instead.

If verification cannot be run, say exactly why and report the remaining risk instead of implying the change is fully proven.
