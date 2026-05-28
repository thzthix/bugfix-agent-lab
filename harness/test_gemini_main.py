from __future__ import annotations

import unittest
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from google.genai import types

from harness.artifacts import (
    RetryContext,
    build_retry_context,
    parse_final_output,
    write_outputs,
)
from harness.gemini_main import read_issue_text, read_prompt
from harness.prompts import build_issue_prompt, build_retry_prompt
from harness.tools import (
    apply_patch_impl,
    build_gemini_tool_config,
    read_file_impl,
    run_tests_impl,
)


class GeminiMainTests(unittest.TestCase):
    def test_read_prompt_uses_explicit_prompt(self) -> None:
        self.assertEqual(read_prompt("hello"), "hello")

    def test_read_issue_text_reads_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            issue_file = Path(temp_dir) / "issue.txt"
            issue_file.write_text("Current failure: example", encoding="utf-8")

            issue_text = read_issue_text(str(issue_file))

        self.assertEqual(issue_text, "Current failure: example")

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

    def test_apply_patch_impl_applies_patch_after_check(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
            target_dir = repo_root / "target-project" / "backend" / "app"
            target_dir.mkdir(parents=True)
            target_file = target_dir / "repository.py"
            target_file.write_text("old\n", encoding="utf-8")
            patch = (
                "--- a/target-project/backend/app/repository.py\n"
                "+++ b/target-project/backend/app/repository.py\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            )

            result = apply_patch_impl(
                repo_root,
                patch,
                ["target-project/backend/app/repository.py"],
            )
            file_text = target_file.read_text(encoding="utf-8")

        self.assertIn("modified_files", result)
        self.assertEqual(file_text, "new\n")

    def test_run_tests_impl_returns_json_summary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)

            result = run_tests_impl(repo_root, "python3 -c \"print('ok')\"")

        self.assertIn("\"success\": true", result)

    def test_build_gemini_tool_config_returns_sdk_config(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            config = build_gemini_tool_config(
                repo_root=repo_root,
                test_command="echo test",
            )

        self.assertIsInstance(config, types.GenerateContentConfig)

    def test_build_issue_prompt_mentions_required_sections(self) -> None:
        prompt = build_issue_prompt("Current task:\nFailure")

        self.assertIn("Current task:\nFailure", prompt)
        self.assertIn("report_markdown", prompt)
        self.assertIn("Chosen Approach", prompt)

    def test_build_retry_prompt_mentions_last_failure(self) -> None:
        retry_context = RetryContext(
            attempt=1,
            max_attempts=3,
            test_command="python3 -m pytest",
            modified_files=["target-project/backend/app/repository.py"],
            test_summary="failed",
            failure_excerpt="AssertionError: completed-state persistence failed.",
        )

        prompt = build_retry_prompt("Current task:\nFailure", retry_context)

        self.assertIn("Attempt: 1 of 3", prompt)
        self.assertIn("target-project/backend/app/repository.py", prompt)
        self.assertIn("AssertionError: completed-state persistence failed.", prompt)

    def test_build_retry_context_reads_last_tool_outputs(self) -> None:
        class FunctionResponse:
            def __init__(self, name: str, response: dict[str, object]) -> None:
                self.name = name
                self.response = response

        class Part:
            def __init__(self, function_response: FunctionResponse) -> None:
                self.function_response = function_response

        class Content:
            def __init__(self, parts: list[Part]) -> None:
                self.parts = parts

        class Response:
            def __init__(self) -> None:
                self.automatic_function_calling_history = [
                    Content(
                        [
                            Part(
                                FunctionResponse(
                                    "apply_patch",
                                    {
                                        "modified_files": [
                                            "target-project/backend/app/repository.py"
                                        ]
                                    },
                                )
                            )
                        ]
                    ),
                    Content(
                        [
                            Part(
                                FunctionResponse(
                                    "run_tests",
                                    {
                                        "command": "python3 -m pytest",
                                        "summary": "failed",
                                        "stderr": "AssertionError: completed-state persistence failed.",
                                        "stdout": "",
                                    },
                                )
                            )
                        ]
                    ),
                ]

        retry_context = build_retry_context(Response(), attempt=1, max_attempts=3)

        self.assertIsNotNone(retry_context)
        self.assertEqual(retry_context.modified_files, ["target-project/backend/app/repository.py"])
        self.assertEqual(retry_context.test_command, "python3 -m pytest")
        self.assertEqual(retry_context.test_summary, "failed")

    def test_parse_final_output_accepts_json(self) -> None:
        payload = parse_final_output(
            json.dumps(
                {
                    "success": True,
                    "summary": "fixed",
                    "modified_files": ["a.py"],
                    "report_markdown": "# Report",
                }
            )
        )

        self.assertEqual(payload["success"], True)
        self.assertEqual(payload["modified_files"], ["a.py"])

    def test_write_outputs_writes_result_and_report(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            payload = {
                "success": True,
                "summary": "fixed",
                "modified_files": ["a.py"],
                "report_markdown": "# Report\n\nDone",
            }

            write_outputs(output_dir, payload)

            result_payload = json.loads(
                (output_dir / "result.json").read_text(encoding="utf-8")
            )
            report_text = (output_dir / "report.md").read_text(encoding="utf-8")

        self.assertEqual(result_payload["summary"], "fixed")
        self.assertEqual(report_text, "# Report\n\nDone")


if __name__ == "__main__":
    unittest.main()
