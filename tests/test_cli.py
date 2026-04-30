from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fluffmods.cli import (
    BEGIN,
    END,
    choose_target_path,
    compile_claude_md,
    load_options,
    nearest_project_claude_path,
    parse_enabled,
    parse_custom_option,
    render_block,
    write_with_backup,
)


class ConfigCompileTests(unittest.TestCase):
    def test_parse_enabled_from_managed_block(self) -> None:
        text = render_block({"codex-delegation", "exact-scope"})

        self.assertEqual(parse_enabled(text), {"codex-delegation", "exact-scope"})

    def test_compile_replaces_existing_managed_block(self) -> None:
        original = f"""# User Preferences

{render_block({"codex-delegation"})}
**Use plugins and MCPs when they're available.**
"""

        compiled = compile_claude_md(original, {"exact-scope"})

        self.assertIn(BEGIN, compiled)
        self.assertIn(END, compiled)
        self.assertIn("exact-scope", compiled)
        self.assertNotIn("codex-delegation -->", compiled)
        self.assertEqual(compiled.count(BEGIN), 1)

    def test_compile_inserts_block_before_anchor(self) -> None:
        original = """# User Preferences

**Break tasks into subtasks; use lighter-weight models where it makes sense.**

**Use plugins and MCPs when they're available.**
"""

        compiled = compile_claude_md(original, {"codex-delegation"})

        self.assertIn("## Codex Delegation Default", compiled)
        self.assertEqual(compiled.count("## Codex Delegation Default"), 1)
        self.assertLess(
            compiled.index(BEGIN),
            compiled.index("**Use plugins and MCPs when they're available.**"),
        )


class WriteTests(unittest.TestCase):
    def test_write_with_backup_creates_backup_for_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "CLAUDE.md"
            path.write_text("old", encoding="utf-8")

            backup = write_with_backup(path, "new")

            self.assertIsNotNone(backup)
            assert backup is not None
            self.assertEqual(path.read_text(encoding="utf-8"), "new")
            self.assertEqual(backup.read_text(encoding="utf-8"), "old")


class CustomOptionTests(unittest.TestCase):
    def test_parse_custom_option_with_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "my-option.md"
            path.write_text(
                """---
id: my-custom-option
label: My Custom Option
---
## My Custom Stanza

Use this behavior.
""",
                encoding="utf-8",
            )

            option = parse_custom_option(path)

            self.assertEqual(option.option_id, "my-custom-option")
            self.assertEqual(option.label, "My Custom Option")
            self.assertIn("Use this behavior.", option.body)
            self.assertEqual(option.source, str(path))

    def test_load_options_includes_custom_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "extra.md"
            path.write_text(
                """# Extra Behavior

Do the extra thing.
""",
                encoding="utf-8",
            )

            options = load_options([tmp], include_default_dirs=False)

            self.assertIn("extra", {option.option_id for option in options})


class TargetSelectionTests(unittest.TestCase):
    def test_nearest_project_claude_path_finds_parent_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_file = root / "CLAUDE.md"
            project_file.write_text("# Project", encoding="utf-8")
            nested = root / "a" / "b"
            nested.mkdir(parents=True)

            self.assertEqual(nearest_project_claude_path(nested), project_file.resolve())

    def test_nearest_project_claude_path_finds_dot_claude_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_file = root / ".claude" / "CLAUDE.md"
            project_file.parent.mkdir()
            project_file.write_text("# Project", encoding="utf-8")
            nested = root / "child"
            nested.mkdir()

            self.assertEqual(nearest_project_claude_path(nested), project_file.resolve())

    def test_choose_target_path_honors_explicit_file(self) -> None:
        self.assertEqual(
            choose_target_path("/tmp/custom-claude.md", assume_global=False, assume_project=False),
            Path("/tmp/custom-claude.md"),
        )


if __name__ == "__main__":
    unittest.main()
