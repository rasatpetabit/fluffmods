from __future__ import annotations

import argparse
import re
import shutil
import sys
import termios
import tty
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


BEGIN = "<!-- BEGIN FLUFF-MODS OPTIONS -->"
END = "<!-- END FLUFF-MODS OPTIONS -->"
META_PREFIX = "<!-- fluffmods: enabled="
AGENTS = ("claude", "codex")
APPLIES_TO = ("generic", "claude", "codex")


@dataclass(frozen=True)
class Option:
    option_id: str
    label: str
    body: str
    applies_to: str = "generic"
    source: str = "bundled"


BUILTIN_OPTIONS: tuple[Option, ...] = (
    Option(
        "codex-delegation",
        "Automatically dispatch simple and well-defined coding tasks to Codex",
        """## Codex Delegation Default

When a coding task is small, well-defined, and can be verified locally, prefer delegating it to Codex by default instead of doing it inline.

Before implementing any self-contained coding subtask, briefly ask: "Can this be safely delegated to Codex?" If yes, delegate it automatically and only keep orchestration/review in Claude.

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
```""",
        applies_to="codex",
    ),
    Option(
        "verify-before-complete",
        "Require local verification before claiming implementation work is done",
        """## Verification Before Completion

Before saying implementation work is complete, run the most relevant local verification commands when they are available and safe. Prefer the repository's own scripts, Makefile targets, package scripts, or documented commands over ad hoc checks.

If verification cannot be run, say exactly why and report the remaining risk instead of implying the change is fully proven.""",
    ),
    Option(
        "protect-user-work",
        "Treat existing uncommitted changes as user-owned",
        """## User-Owned Worktree Changes

Treat existing uncommitted changes as user-owned. Do not revert, overwrite, reformat, or "clean up" unrelated changes unless the user explicitly asks for that operation.

When unrelated dirty files are present, work around them and keep the final report scoped to the files intentionally changed.""",
    ),
    Option(
        "review-findings-first",
        "Use findings-first format for code reviews",
        """## Code Review Response Shape

When asked for a code review, lead with findings ordered by severity. Ground each finding in a file path and line number when possible. Keep summaries secondary and short.

If there are no blocking issues, say that directly and call out any residual test or runtime risk.""",
    ),
    Option(
        "plan-complex-work",
        "Plan before multi-file or ambiguous implementation work",
        """## Planning Threshold

For multi-file changes, new features, migrations, or ambiguous design work, produce a short execution plan before editing. Keep one-shot fixes lightweight and execute directly.""",
    ),
    Option(
        "prefer-project-runbooks",
        "Prefer project-local runbooks and scripts over generic commands",
        """## Project-Local Tooling First

Before inventing generic commands, look for project-local runbooks, Makefile targets, package scripts, CI definitions, and existing test helpers. Use the repository's established path unless there is a clear reason not to.""",
    ),
    Option(
        "concise-final-report",
        "Keep final reports compact and evidence-backed",
        """## Concise Final Reports

Final reports should be compact. Include what changed, what was verified, and any blocker or residual risk. Avoid long explanations unless the user asks for the reasoning or the work genuinely needs it.""",
    ),
    Option(
        "durable-handoff",
        "Write durable handoff notes for substantive multi-step work",
        """## Durable Handoff Notes

For substantive multi-step work, preserve durable state in the repository when an existing handoff surface is present, such as WORKLOG.md, docs/collaboration/status.md, or a task file. Record decisions and next steps, not a verbose transcript.""",
    ),
    Option(
        "ask-for-risky-actions",
        "Ask before destructive, external, or production-visible actions",
        """## Risky Action Approval

Ask before destructive operations, production-visible changes, force pushes, broad permission changes, external messages, or actions requiring secrets or privileged account approval. Keep ordinary local inspection, edits, and tests self-service.""",
    ),
    Option(
        "exact-scope",
        "Honor exact file and task scope literally",
        """## Exact Scope Discipline

When the user gives an exact file list, numbered task, or "only edit" boundary, treat it as binding. Do not compensate by editing adjacent helpers, formatting unrelated files, or broadening the task without approval.""",
    ),
    Option(
        "output-important-command-results",
        "Relay important command output instead of just saying commands ran",
        """## Command Output Reporting

When command output is important to the user's request, relay the relevant lines or summarize the concrete result. Do not assume the user can see terminal output.""",
    ),
)


def option_map(options: tuple[Option, ...]) -> dict[str, Option]:
    return {option.option_id: option for option in options}


def option_applies_to_agent(option: Option, agent: str) -> bool:
    return option.applies_to == "generic" or option.applies_to == agent


def options_for_agent(options: tuple[Option, ...], agent: str) -> tuple[Option, ...]:
    return tuple(option for option in options if option_applies_to_agent(option, agent))


def global_guidance_path(agent: str) -> Path:
    if agent == "codex":
        return Path.home() / ".codex" / "AGENTS.md"
    return Path.home() / ".claude" / "CLAUDE.md"


def guidance_path(path_arg: str | None, agent: str) -> Path:
    if path_arg:
        return Path(path_arg).expanduser()
    return global_guidance_path(agent)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def project_guidance_candidates(directory: Path, agent: str) -> tuple[Path, ...]:
    if agent == "codex":
        return (
            directory / "AGENTS.md",
            directory / ".codex" / "AGENTS.md",
        )
    return (
        directory / "CLAUDE.md",
        directory / ".claude" / "CLAUDE.md",
    )


def nearest_project_guidance_path(agent: str, start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for directory in (current, *current.parents):
        for candidate in project_guidance_candidates(directory, agent):
            if candidate.exists():
                return candidate

    return None


def choose_target_path(
    path_arg: str | None,
    assume_global: bool,
    assume_project: bool,
    agent: str,
) -> Path:
    if path_arg:
        return guidance_path(path_arg, agent)

    global_path = global_guidance_path(agent)
    project_path = nearest_project_guidance_path(agent)

    if assume_global:
        return global_path
    if assume_project:
        return project_path or global_path

    if not project_path or project_path == global_path:
        return global_path

    if not sys.stdin.isatty():
        print(
            f"Project {agent} guidance detected at {project_path}; using global {global_path}. "
            "Pass --project or --file to edit the project file.",
            file=sys.stderr,
        )
        return global_path

    print(f"Project {agent} guidance detected: {project_path}")
    print(f"Global {agent} guidance:           {global_path}")
    while True:
        choice = input("Edit project or global guidance? [p/g/q] ").strip().lower()
        if choice in {"p", "project"}:
            return project_path
        if choice in {"g", "global", ""}:
            return global_path
        if choice in {"q", "quit", "exit"}:
            raise KeyboardInterrupt
        print("Enter p for project, g for global, or q to quit.")


def slugify_option_id(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "custom-option"


def label_from_body(body: str, fallback: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def parse_custom_option(path: Path) -> Option:
    text = read_text(path).strip()
    metadata: dict[str, str] = {}
    body = text

    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            raw_metadata = text[4:end]
            body = text[end + len("\n---") :].lstrip()
            for line in raw_metadata.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip().strip('"').strip("'")

    fallback_label = path.stem.replace("-", " ").replace("_", " ").title()
    option_id = slugify_option_id(metadata.get("id", path.stem))
    label = metadata.get("label") or label_from_body(body, fallback_label)
    applies_to = metadata.get("applies_to", "generic").strip().lower()
    if applies_to not in APPLIES_TO:
        raise ValueError(
            f"{path} has invalid applies_to {applies_to!r}; expected one of {', '.join(APPLIES_TO)}"
        )

    if not body:
        raise ValueError(f"{path} has no stanza body")

    return Option(
        option_id=option_id,
        label=label,
        body=body,
        applies_to=applies_to,
        source=str(path),
    )


def default_option_dirs() -> list[Path]:
    return [
        Path.home() / ".config" / "fluffmods" / "options",
        Path.cwd() / ".fluffmods" / "options",
    ]


def load_options(extra_dirs: list[str] | None = None, include_default_dirs: bool = True) -> tuple[Option, ...]:
    options = list(BUILTIN_OPTIONS)
    seen = {option.option_id for option in options}
    dirs = default_option_dirs() if include_default_dirs else []
    dirs.extend(Path(item).expanduser() for item in extra_dirs or [])

    for directory in dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            option = parse_custom_option(path)
            if option.option_id in seen:
                raise ValueError(
                    f"Duplicate option id {option.option_id!r} from {path}; choose a unique id"
                )
            options.append(option)
            seen.add(option.option_id)

    return tuple(options)


def parse_enabled(text: str) -> set[str]:
    block = extract_managed_block(text)
    if block:
        match = re.search(r"<!-- fluffmods: enabled=([^>]*) -->", block)
        if match:
            raw = match.group(1).strip()
            if not raw:
                return set()
            return {item.strip() for item in raw.split(",") if item.strip()}

    return set()


def extract_managed_block(text: str) -> str | None:
    start = text.find(BEGIN)
    end = text.find(END)
    if start == -1 or end == -1 or end < start:
        return None
    return text[start : end + len(END)]


def remove_managed_block(text: str) -> str:
    pattern = re.compile(
        rf"\n?{re.escape(BEGIN)}.*?{re.escape(END)}\n?",
        flags=re.DOTALL,
    )
    return pattern.sub("\n", text).strip() + "\n"


def render_block(enabled: set[str], options: tuple[Option, ...] = BUILTIN_OPTIONS) -> str:
    ids = [option.option_id for option in options if option.option_id in enabled]
    lines = [
        BEGIN,
        f"{META_PREFIX}{','.join(ids)} -->",
        "",
        "## Managed Claude Behavior Options",
        "",
        "This section is generated by `fluffmods`. Toggle options with `fluffmods` instead of editing this block by hand.",
        "",
    ]

    for option in options:
        if option.option_id not in enabled:
            continue
        lines.append(option.body.rstrip())
        lines.append("")

    lines.append(END)
    lines.append("")
    return "\n".join(lines)


def compile_claude_md(
    original: str,
    enabled: set[str],
    options: tuple[Option, ...] = BUILTIN_OPTIONS,
) -> str:
    text = remove_managed_block(original)
    block = render_block(enabled, options)

    anchor = "**Use plugins and MCPs when they're available.**"
    index = text.find(anchor)
    if index != -1:
        before = text[:index].rstrip()
        after = text[index:].lstrip()
        return f"{before}\n\n{block}\n{after}".rstrip() + "\n"

    return text.rstrip() + "\n\n" + block


def write_with_backup(path: Path, content: str) -> Path | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.name}.fluffmods-{stamp}.bak")
        shutil.copy2(path, backup)
    path.write_text(content, encoding="utf-8")
    return backup


def print_status(enabled: set[str], options: tuple[Option, ...] = BUILTIN_OPTIONS) -> None:
    for index, option in enumerate(options, start=1):
        mark = "x" if option.option_id in enabled else " "
        source = "bundled" if option.source == "bundled" else "custom"
        print(
            f"{index:2}. [{mark}] {option.label}  "
            f"({option.option_id}, {option.applies_to}, {source})"
        )


def print_menu(
    enabled: set[str],
    selected_index: int,
    path: Path,
    options: tuple[Option, ...],
) -> None:
    print("\033[2J\033[H", end="")
    print(f"fluffmods: {path}")
    print("Use ↑/↓ to move, space to toggle, enter/a to apply, p to preview, q to quit.")
    print()

    for index, option in enumerate(options):
        pointer = ">" if index == selected_index else " "
        mark = "x" if option.option_id in enabled else " "
        source = "bundled" if option.source == "bundled" else "custom"
        print(
            f"{pointer} {index + 1:2}. [{mark}] {option.label}  "
            f"({option.option_id}, {option.applies_to}, {source})"
        )


def read_key() -> str:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        char = sys.stdin.read(1)
        if char == "\x1b":
            attrs = termios.tcgetattr(fd)
            attrs[6][termios.VMIN] = 0
            attrs[6][termios.VTIME] = 5
            termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
            sequence = ""
            for _ in range(4):
                next_char = sys.stdin.read(1)
                if not next_char:
                    break
                sequence += next_char
                if sequence in {"[A", "[B", "OA", "OB"}:
                    break
            if sequence in {"[A", "OA"}:
                return "up"
            if sequence in {"[B", "OB"}:
                return "down"
            return "escape"
        if char in {"\r", "\n"}:
            return "enter"
        if char == " ":
            return "space"
        return char.lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def normalize_ids(ids: list[str], options: tuple[Option, ...]) -> set[str]:
    valid = option_map(options)
    unknown = [item for item in ids if item not in valid]
    if unknown:
        print(f"Unknown option id(s): {', '.join(unknown)}", file=sys.stderr)
        sys.exit(2)
    return set(ids)


def interactive(path: Path, enabled: set[str], options: tuple[Option, ...]) -> set[str] | None:
    if sys.stdin.isatty() and sys.stdout.isatty():
        selected_index = 0
        while True:
            print_menu(enabled, selected_index, path, options)
            key = read_key()

            if key == "q":
                print("\033[2J\033[H", end="")
                return None
            if key == "escape":
                continue
            if key in {"a", "enter"}:
                print("\033[2J\033[H", end="")
                return enabled
            if key == "p":
                print("\033[2J\033[H", end="")
                print(render_block(enabled, options))
                input("Press enter to return to the menu...")
                continue
            if key in {"up", "k"}:
                selected_index = (selected_index - 1) % len(options)
                continue
            if key in {"down", "j"}:
                selected_index = (selected_index + 1) % len(options)
                continue
            if key == "space":
                option_id = options[selected_index].option_id
                if option_id in enabled:
                    enabled.remove(option_id)
                else:
                    enabled.add(option_id)
                continue
            if key.isdigit():
                index = int(key) - 1
                if 0 <= index < len(options):
                    selected_index = index
                    continue

    print(f"fluffmods: {path}")
    print("Toggle options by number. Commands: p=preview, a=apply, q=quit")

    while True:
        print()
        print_status(enabled, options)
        choice = input("\nChoice: ").strip().lower()

        if choice in {"q", "quit", "exit"}:
            return None
        if choice in {"a", "apply"}:
            return enabled
        if choice in {"p", "preview"}:
            print()
            print(render_block(enabled, options))
            continue
        if not choice:
            continue
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(options):
                option_id = options[index].option_id
                if option_id in enabled:
                    enabled.remove(option_id)
                else:
                    enabled.add(option_id)
                continue
        print("Enter an option number, p, a, or q.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Claude + Fluff-Mods: checkbox-style manager for Claude Code and Codex guidance."
    )
    parser.add_argument(
        "--agent",
        choices=AGENTS,
        default="claude",
        help="Guidance target family, defaults to claude",
    )
    parser.add_argument("--claude", dest="agent_override", action="store_const", const="claude", help="Shortcut for --agent claude")
    parser.add_argument("--codex", dest="agent_override", action="store_const", const="codex", help="Shortcut for --agent codex")
    parser.add_argument("--file", help="Path to guidance file; bypasses agent default target discovery")
    parser.add_argument("--global", dest="assume_global", action="store_true", help="Edit the selected agent's global guidance file without prompting")
    parser.add_argument("--project", dest="assume_project", action="store_true", help="Edit the selected agent's nearest project guidance file without prompting")
    parser.add_argument("--status", action="store_true", help="Print current option status")
    parser.add_argument("--preview", action="store_true", help="Print generated managed block")
    parser.add_argument("--apply", action="store_true", help="Apply selected options")
    parser.add_argument("--enable", action="append", default=[], help="Enable option id")
    parser.add_argument("--disable", action="append", default=[], help="Disable option id")
    parser.add_argument(
        "--options-dir",
        action="append",
        default=[],
        help="Load custom option .md files from this directory",
    )
    parser.add_argument(
        "--no-default-option-dirs",
        action="store_true",
        help="Do not auto-load ~/.config/fluffmods/options or ./.fluffmods/options",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.assume_global and args.assume_project:
        parser.error("--global and --project are mutually exclusive")
    agent = args.agent_override or args.agent

    try:
        path = choose_target_path(args.file, args.assume_global, args.assume_project, agent)
    except KeyboardInterrupt:
        print("No changes applied.")
        return 0

    original = read_text(path)
    enabled = parse_enabled(original)
    all_options = load_options(args.options_dir, not args.no_default_option_dirs)
    options = options_for_agent(all_options, agent)

    enabled.update(normalize_ids(args.enable, options))
    enabled.difference_update(normalize_ids(args.disable, options))

    if args.status:
        print_status(enabled, options)
        return 0

    if args.preview:
        print(render_block(enabled, options))
        return 0

    if args.apply:
        compiled = compile_claude_md(original, enabled, options)
        backup = write_with_backup(path, compiled)
        print(f"Updated {path}")
        if backup:
            print(f"Backup: {backup}")
        return 0

    selected = interactive(path, enabled, options)
    if selected is None:
        print("No changes applied.")
        return 0

    compiled = compile_claude_md(original, selected, options)
    backup = write_with_backup(path, compiled)
    print(f"Updated {path}")
    if backup:
        print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
