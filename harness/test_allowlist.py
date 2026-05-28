from __future__ import annotations

import unittest

from harness.allowlist import (
    AllowlistResolutionError,
    build_task_input,
    extract_error_paths,
    extract_error_summary,
    resolve_allowed_files,
)


CODE_MAP_TEXT = """
# Code Map

- `backend/app/models.py`
  Domain models and API-facing data shapes for todo items.
- `backend/app/repository.py`
  JSON-backed persistence and reload behavior.
- `backend/app/service.py`
  Todo business logic such as create, toggle, favorite, filtering, and summaries.
- `backend/app/main.py`
  FastAPI routes used by the frontend.
- `backend/tests/test_service.py`
  Behavior verification for the first bug-fix exercise.
"""


class AllowlistTests(unittest.TestCase):
    def test_extract_error_paths_finds_paths_in_issue_text(self) -> None:
        issue_text = """
        AssertionError in `target-project/backend/tests/test_service.py`
        and stack trace through target-project/backend/app/repository.py
        """

        paths = extract_error_paths(issue_text)

        self.assertEqual(
            paths,
            [
                "target-project/backend/tests/test_service.py",
                "target-project/backend/app/repository.py",
            ],
        )

    def test_resolve_allowed_files_filters_to_backend_app_paths(self) -> None:
        error_paths = [
            "target-project/backend/tests/test_service.py",
            "target-project/backend/app/repository.py",
        ]

        allowed_files = resolve_allowed_files(error_paths, CODE_MAP_TEXT)

        self.assertEqual(
            allowed_files,
            [
                "target-project/backend/app/repository.py",
                "target-project/backend/app/models.py",
                "target-project/backend/app/service.py",
            ],
        )

    def test_resolve_allowed_files_uses_fallback_candidates(self) -> None:
        error_paths = ["target-project/backend/tests/test_service.py"]

        allowed_files = resolve_allowed_files(error_paths, CODE_MAP_TEXT)

        self.assertIn("target-project/backend/app/models.py", allowed_files)
        self.assertIn("target-project/backend/app/repository.py", allowed_files)
        self.assertIn("target-project/backend/app/service.py", allowed_files)

    def test_resolve_allowed_files_fails_when_nothing_is_allowed(self) -> None:
        with self.assertRaises(AllowlistResolutionError):
            resolve_allowed_files(
                ["target-project/frontend/src/App.tsx"],
                CODE_MAP_TEXT,
            )

    def test_extract_error_summary_prefers_error_line(self) -> None:
        issue_text = """
        Grocery list toggle bug

        AssertionError: completed-state persistence is inconsistent after reload.
        Seen in `target-project/backend/tests/test_service.py`
        """

        summary = extract_error_summary(issue_text)

        self.assertEqual(
            summary,
            "AssertionError: completed-state persistence is inconsistent after reload.",
        )

    def test_build_task_input_formats_allowed_files_and_tests(self) -> None:
        task_input = build_task_input(
            issue_text=(
                "Issue title\n\n"
                "Current failure: completed-state persistence is inconsistent "
                "after reload."
            ),
            allowed_files=[
                "target-project/backend/app/models.py",
                "target-project/backend/app/repository.py",
            ],
        )

        self.assertIn("Current task:", task_input)
        self.assertIn(
            "Current failure: completed-state persistence is inconsistent after reload.",
            task_input,
        )
        self.assertIn("Allowed files for this task:", task_input)
        self.assertIn("target-project/backend/app/models.py", task_input)
        self.assertIn("Relevant tests:", task_input)


if __name__ == "__main__":
    unittest.main()
