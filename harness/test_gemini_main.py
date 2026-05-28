from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from google.genai import types

from harness.gemini_main import (
    apply_patch_impl,
    build_generate_content_config,
    read_file_impl,
    read_prompt,
    run_tests_impl,
)


class GeminiMainTests(unittest.TestCase):
    def test_read_prompt_uses_explicit_prompt(self) -> None:
        self.assertEqual(read_prompt("hello"), "hello")

    def test_read_file_impl_rejects_disallowed_path(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)

            with self.assertRaisesRegex(ValueError, "Read path is not allowed"):
                read_file_impl(repo_root, "README.md")

    def test_read_file_impl_returns_full_text_for_allowed_path(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            target_dir = repo_root / "target-project" / "backend" / "app"
            target_dir.mkdir(parents=True)
            expected = "def save_items():\n    return True\n"
            (target_dir / "repository.py").write_text(expected, encoding="utf-8")

            content = read_file_impl(
                repo_root,
                "target-project/backend/app/repository.py",
            )

        self.assertEqual(content, expected)

    def test_apply_patch_impl_returns_json_summary(self) -> None:
        result = apply_patch_impl(
            "--- a/x.py\n+++ b/target-project/backend/app/repository.py\n@@\n-old\n+new\n"
        )

        self.assertIn("modified_files", result)

    def test_run_tests_impl_returns_json_summary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)

            result = run_tests_impl(repo_root, "python3 -c \"print('ok')\"")

        self.assertIn("\"success\": true", result)

    def test_build_generate_content_config_returns_sdk_config(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            config = build_generate_content_config(
                repo_root=repo_root,
                test_command="echo test",
            )

        self.assertIsInstance(config, types.GenerateContentConfig)


if __name__ == "__main__":
    unittest.main()
