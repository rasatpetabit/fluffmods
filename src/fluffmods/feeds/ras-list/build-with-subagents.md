---
id: build-with-subagents
label: Build with subagents while keeping the critical path local
version: 1.0.0
updated_on: 2026-05-01
---
## Build With Subagents

When executing a plan, parallelize independent steps where useful, but do not delegate blocking work. Keep the critical path moving locally while subagents handle non-overlapping side tasks.
