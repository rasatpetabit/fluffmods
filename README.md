# AI + FluffMods

`fluffmods` is a multi-agent guidance manager for turning long agent
behavior directives into simple on/off options. It supports Claude Code, Codex,
and custom agent guidance files; ships with manicured built-in feeds of
high-leverage directives; and lets users subscribe to additional feeds from
their favorite authors.

It edits one managed block in the selected guidance file and leaves the rest of
the file alone. Claude targets use `CLAUDE.md`; Codex targets use `AGENTS.md`.
The default feed is `RAS list`, which is enabled natively.

## Install

From GitHub:

```sh
pipx install git+https://github.com/rasatpetabit/fluffmods.git
```

Or with `uv`:

```sh
uv tool install git+https://github.com/rasatpetabit/fluffmods.git
```

For local development:

```sh
git clone https://github.com/rasatpetabit/fluffmods.git
cd fluffmods
python3 -m pip install -e .
```

## Use

Open the interactive menu:

```sh
fluffmods
```

If you run `fluffmods` inside a project that already has `CLAUDE.md` or
`.claude/CLAUDE.md`, it asks whether you want to edit that project guidance or
your global `~/.claude/CLAUDE.md`.

For Codex, use `--codex` or `--agent codex`. Global Codex guidance targets
`~/.codex/AGENTS.md`, and project discovery looks for `AGENTS.md` or
`.codex/AGENTS.md`.

Options that apply to both agents are shown without a special tag. Agent-specific
options are tagged as `claude-only` or `codex-only` and are shown only for that
selected agent.

The menu supports arrow-key navigation. Use up/down arrows to move, space to
toggle an option, `D` to view the complete stanza, `E` to erase a custom stanza
after confirmation, `U` to upgrade all enabled stanzas to the latest feed
versions, `P` to preview, `Q` to quit, and enter or `A` to apply. Uppercase and
lowercase commands are both accepted.

Check current option state:

```sh
fluffmods --status
fluffmods --codex --status
```

Preview the generated guidance block:

```sh
fluffmods --preview
```

Enable or disable options non-interactively:

```sh
fluffmods --enable codex-delegation --apply
fluffmods --disable codex-delegation --apply
fluffmods --codex --enable exact-scope --apply
fluffmods --upgrade
```

Use a different target file:

```sh
fluffmods --file ./CLAUDE.md --enable verify-before-complete --apply
```

Skip the target prompt:

```sh
fluffmods --project
fluffmods --global
fluffmods --codex --project
fluffmods --codex --global
```

Load custom stanza files from a directory:

```sh
fluffmods --options-dir ./my-claude-options --status
```

Manage feeds:

```sh
fluffmods --feed-list
fluffmods --feed-add https://example.com/path/to/feed.json
fluffmods --feed-remove feed-id
fluffmods --feed-refresh
```

fluffmods loads the currently installed feed cache immediately. In interactive
mode, it checks enabled remote feeds in the background when a feed has not been
refreshed for more than an hour, then tells you whether refresh succeeded or
failed.

Configure automatic upgrades of existing guidance files to the latest feed
versions:

```sh
fluffmods --auto-update-configs status
fluffmods --auto-update-configs on
fluffmods --auto-update-configs off
```

Each feed stanza can include `version` and `updated_on` metadata. fluffmods
records that metadata in the managed block, compares older installs against the
current feed body, and marks enabled stanzas with `refresh available` when the
installed copy differs.

## Included Options

These ship in the default `RAS list` feed.

- `ask-user-directly`: Ask the user directly when input is needed.
- `context-discipline`: Keep context usage disciplined in large ongoing work.
- `codex-delegation` (`claude-only`): Automatically dispatch simple and well-defined coding tasks to Codex.
- `verify-before-complete`: Require local verification before claiming implementation work is done.
- `protect-user-work`: Treat existing uncommitted changes as user-owned.
- `review-findings-first`: Use findings-first format for code reviews.
- `plan-complex-work`: Plan before multi-file or ambiguous implementation work.
- `build-with-subagents`: Build with subagents while keeping the critical path local.
- `prefer-project-runbooks`: Prefer project-local runbooks and scripts over ad hoc commands.
- `concise-final-report`: Keep final reports compact and evidence-backed.
- `durable-handoff`: Write durable handoff notes for substantive multi-step work.
- `ask-for-risky-actions`: Ask before destructive, external, or production-visible actions.
- `exact-scope`: Honor exact file and task scope literally.
- `output-important-command-results`: Relay important command output instead of just saying commands ran.

## Custom Options

Custom options are Markdown files. Put them in either:

```text
~/.config/fluffmods/options/
./.fluffmods/options/
```

Or point at a directory explicitly:

```sh
fluffmods --options-dir ./options
```

The simplest custom option uses the filename as the option id and the first
Markdown heading as the menu label:

```md
# Prefer Small Pull Requests

When implementation work grows beyond one clear review unit, split it into
smaller commits or handoff tasks before continuing.
```

For stable ids and labels, add front matter:

```md
---
id: small-prs
label: Prefer small pull requests
applies_to: claude-only
---

# Prefer Small Pull Requests

When implementation work grows beyond one clear review unit, split it into
smaller commits or handoff tasks before continuing.
```

Set `applies_to: claude-only` or `applies_to: codex-only` for an agent-specific
option. Omit `applies_to` when an option should be available for both agents.

The intended model is:

- **Bundled stanzas:** useful defaults that ship with fluffmods.
- **Custom stanzas:** your own reusable `CLAUDE.md` blocks, stored as Markdown
  files and toggled through the same interface.
- **Adopted current stanzas:** future work will make it easy to extract existing
  unmanaged `CLAUDE.md` sections into custom option files.

## How It Works

`fluffmods` owns this block in whichever guidance file you choose:

```md
<!-- BEGIN FLUFF-MODS OPTIONS -->
...
<!-- END FLUFF-MODS OPTIONS -->
```

The tool stores enabled option ids in a metadata comment inside that block. On
apply, it regenerates only the managed block and makes a timestamped backup of
the target guidance file under `~/.cache/fluffmods/backups/`.

If no managed block exists yet, the tool appends one.

## Safety

- No runtime dependencies.
- Does not edit `~/.claude/settings.json` or `~/.claude.json`.
- Creates a cache-directory backup before writing, so edited folders are not
  cluttered with `.bak` files.
- Supports `--preview` for dry-run inspection.
- After applying, asks the target agent (Claude for Claude config, Codex for
  Codex config) to audit the selected stanzas for conflicts and harmful
  directives that may indicate a compromised feed. The local heuristic summary
  prints first, then the target agent runs in a fast/low-effort analysis mode.
  The agent is asked for structured JSON, which fluffmods renders as
  compact terminal-friendly severity blocks with 1-5 ratings and emoji bars.

## License

GPL-3.0-or-later.

## Development

Run tests:

```sh
python3 -m unittest discover -s tests
```
