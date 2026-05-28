from __future__ import annotations

import io
import json
import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from harness.config import LoopResult
from harness.main import main, read_issue_text


class MainTests(unittest.TestCase):
    def test_read_issue_text_reads_from_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            issue_file = Path(temp_dir) / "issue.txt"
            issue_file.write_text("Current failure: example", encoding="utf-8")

            issue_text = read_issue_text(str(issue_file))

        self.assertEqual(issue_text, "Current failure: example")

    def test_main_runs_loop_and_prints_json_result(self) -> None:
        fake_result = LoopResult(
            success=True,
            attempts=1,
            allowed_files=["target-project/backend/app/repository.py"],
            final_response_id="resp_1",
            last_test_summary="passed",
            tool_history=[],
        )

        captured_stdout = io.StringIO()

        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            args = Namespace(repo_root=str(repo_root), issue_file=None)

            with patch("harness.main.parse_args", return_value=args), patch(
                "harness.main.read_issue_text",
                return_value="Current failure: AssertionError",
            ), patch("harness.main.create_client", return_value=object()), patch(
                "harness.main.HarnessLoop"
            ) as loop_cls, patch("sys.stdout", new=captured_stdout):
                loop_cls.return_value.run.return_value = fake_result

                exit_code = main()

        self.assertEqual(exit_code, 0)
        loop_cls.return_value.run.assert_called_once_with(
            "Current failure: AssertionError"
        )
        payload = json.loads(captured_stdout.getvalue())
        self.assertEqual(payload["success"], True)
        self.assertEqual(payload["attempts"], 1)
        self.assertEqual(payload["last_test_summary"], "passed")


if __name__ == "__main__":
    unittest.main()
