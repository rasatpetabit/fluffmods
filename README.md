# Fluff-Mods

`Fluff-Mods` is a multi-agent guidance manager for turning long agent
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

Options are tagged as `generic`, `claude`, or `codex`. Generic options are shown
for both agents; Claude and Codex options are shown only for that selected agent.

The menu supports arrow-key navigation. Use up/down arrows to move, space to
toggle an option, `R` to refresh a selected stale stanza, `U` to upgrade all
enabled stanzas to the latest feed versions, `d` to delete a custom stanza after
confirmation, `p` to preview, and enter or `a` to apply.

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

Fluff-Mods loads the currently installed feed cache immediately. In interactive
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

Each feed stanza can include `version` and `updated_on` metadata. Fluff-Mods
records that metadata in the managed block, compares older installs against the
current feed body, and marks enabled stanzas with `refresh available` when the
installed copy differs.

## Included Options

These ship in the default `RAS list` feed.

- `codex-delegation` (`claude`): Automatically dispatch simple and well-defined coding tasks to Codex.
- `verify-before-complete` (`generic`): Require local verification before claiming implementation work is done.
- `protect-user-work` (`generic`): Treat existing uncommitted changes as user-owned.
- `review-findings-first` (`generic`): Use findings-first format for code reviews.
- `plan-complex-work` (`generic`): Plan before multi-file or ambiguous implementation work.
- `prefer-project-runbooks` (`generic`): Prefer project-local runbooks and scripts over generic commands.
- `concise-final-report` (`generic`): Keep final reports compact and evidence-backed.
- `durable-handoff` (`generic`): Write durable handoff notes for substantive multi-step work.
- `ask-for-risky-actions` (`generic`): Ask before destructive, external, or production-visible actions.
- `exact-scope` (`generic`): Honor exact file and task scope literally.
- `output-important-command-results` (`generic`): Relay important command output instead of just saying commands ran.

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
applies_to: generic
---

# Prefer Small Pull Requests

When implementation work grows beyond one clear review unit, split it into
smaller commits or handoff tasks before continuing.
```

`applies_to` may be `generic`, `claude`, or `codex`. If omitted, it defaults to
`generic`.

The intended model is:

- **Bundled stanzas:** useful defaults that ship with Fluff-Mods.
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
the target `CLAUDE.md`.

If no managed block exists yet, the tool appends one.

## Safety

- No runtime dependencies.
- Does not edit `~/.claude/settings.json` or `~/.claude.json`.
- Creates a backup before writing.
- Supports `--preview` for dry-run inspection.
- After applying, asks the target agent (`claude` for Claude config, `codex` for
  Codex config) to audit the selected stanzas for conflicts and suspicious
  directives that may indicate a compromised feed, then prints the local
  heuristic fallback summary.

## License

GPL-3.0-or-later.

## Development

Run tests:

```sh
python3 -m unittest discover -s tests
```
