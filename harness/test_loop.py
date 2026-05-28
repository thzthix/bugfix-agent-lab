from __future__ import annotations

import json
import unittest
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from harness.config import (
    DEFAULT_TEST_COMMAND,
    HarnessLoopError,
    LoopConfig,
)
from harness.decisions import handle_test_result
from harness.loop import HarnessLoop
from harness.response_api import build_instructions
from harness.task import build_loop_context
from harness.tools import build_tools


@dataclass
class FakeOutputItem:
    type: str
    call_id: str | None = None
    name: str | None = None
    arguments: str | None = None


@dataclass
class FakeResponse:
    id: str
    output: list[FakeOutputItem]


class FakeResponsesClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = responses
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = FakeResponsesClient(responses)


def _make_result(tool_name: str, output: dict) -> object:
    class Result:
        def __init__(self, tool_name: str, output: dict) -> None:
            self.tool_name = tool_name
            self.output = output

    return Result(tool_name, output)


class LoopTests(unittest.TestCase):
    def test_build_tools_contains_three_function_tools(self) -> None:
        tools = build_tools()

        self.assertEqual(len(tools), 3)
        self.assertEqual([tool["name"] for tool in tools], ["read_file", "apply_patch", "run_tests"])

    def test_build_instructions_mentions_goal_and_stop_conditions(self) -> None:
        instructions = build_instructions()

        self.assertIn("Fix the bug and make all tests pass.", instructions)
        self.assertIn("Fail if the tests still do not pass after 3 attempts.", instructions)

    def test_handle_test_result_returns_continue_without_run_tests(self) -> None:
        decision = handle_test_result(
            [
                _make_result("read_file", {"content": "x"}),
                _make_result("apply_patch", {"success": True}),
            ]
        )

        self.assertEqual(decision, "continue")

    def test_handle_test_result_returns_passed_on_successful_test_run(self) -> None:
        decision = handle_test_result(
            [
                _make_result(
                    "run_tests",
                    {"success": True, "summary": "passed"},
                )
            ]
        )

        self.assertEqual(decision, "passed")

    def test_handle_test_result_returns_failed_on_failed_test_run(self) -> None:
        decision = handle_test_result(
            [
                _make_result(
                    "run_tests",
                    {"success": False, "summary": "failed"},
                )
            ]
        )

        self.assertEqual(decision, "failed")

    def test_apply_patch_rejects_files_outside_allowlist(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            loop = HarnessLoop(
                client=FakeClient([]),
                config=LoopConfig(repo_root=repo_root, test_command=DEFAULT_TEST_COMMAND),
            )

            with self.assertRaises(HarnessLoopError):
                loop._apply_patch(
                    "+++ b/target-project/frontend/src/App.tsx\n+change",
                    ["target-project/backend/app/repository.py"],
                )

    def test_execute_tool_calls_returns_execution_results_and_response_inputs(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            _seed_repo(repo_root)
            loop = HarnessLoop(
                client=FakeClient([]),
                config=LoopConfig(repo_root=repo_root, test_command=DEFAULT_TEST_COMMAND),
            )

            execution_results, response_inputs = loop.execute_tool_calls(
                [
                    {
                        "call_id": "call_1",
                        "name": "read_file",
                        "arguments": {
                            "path": "target-project/backend/app/repository.py",
                        },
                    }
                ],
                context=build_loop_context(
                    issue_text="Current failure: AssertionError in target-project/backend/tests/test_service.py",
                    repo_root=repo_root,
                ),
            )

        self.assertEqual(len(execution_results), 1)
        self.assertEqual(execution_results[0].tool_name, "read_file")
        self.assertEqual(len(response_inputs), 1)
        self.assertEqual(response_inputs[0]["type"], "function_call_output")
        self.assertEqual(response_inputs[0]["call_id"], "call_1")

    def test_apply_decision_preserves_last_test_summary_on_continue(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            _seed_repo(repo_root)
            loop = HarnessLoop(
                client=FakeClient([]),
                config=LoopConfig(repo_root=repo_root, test_command=DEFAULT_TEST_COMMAND),
            )
            context = build_loop_context(
                issue_text="Current failure: AssertionError in target-project/backend/tests/test_service.py",
                repo_root=repo_root,
            )

            attempts, last_test_summary, result = loop._apply_decision(
                decision="continue",
                attempts=1,
                context=context,
                previous_response_id="resp_1",
                current_last_test_summary="failed",
                tool_history=[],
            )

        self.assertEqual(attempts, 1)
        self.assertEqual(last_test_summary, "failed")
        self.assertIsNone(result)

    def test_send_tool_outputs_uses_previous_response_id(self) -> None:
        fake_client = FakeClient(
            [
                FakeResponse(
                    id="resp_1",
                    output=[
                        FakeOutputItem(
                            type="function_call",
                            call_id="call_1",
                            name="read_file",
                            arguments=json.dumps(
                                {"path": "target-project/backend/app/repository.py"}
                            ),
                        )
                    ],
                ),
                FakeResponse(id="resp_2", output=[]),
                FakeResponse(id="resp_3", output=[]),
            ]
        )
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            _seed_repo(repo_root)
            loop = HarnessLoop(
                client=fake_client,
                config=LoopConfig(
                    repo_root=repo_root,
                    test_command="python3 -c \"print('ok')\"",
                ),
            )

            result = loop.run(
                "Current failure: AssertionError in target-project/backend/tests/test_service.py"
            )

        self.assertFalse(result.success)
        self.assertEqual(fake_client.responses.calls[1]["previous_response_id"], "resp_1")

    def test_start_response_uses_task_input_for_first_request(self) -> None:
        fake_client = FakeClient([FakeResponse(id="resp_1", output=[])])
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            _seed_repo(repo_root)
            loop = HarnessLoop(
                client=fake_client,
                config=LoopConfig(repo_root=repo_root, test_command=DEFAULT_TEST_COMMAND),
            )
            context = build_loop_context(
                issue_text="Current failure: AssertionError in target-project/backend/tests/test_service.py",
                repo_root=repo_root,
            )

            response = loop.start_response(context=context, previous_response_id=None)

        self.assertEqual(response.id, "resp_1")
        self.assertEqual(fake_client.responses.calls[0]["input"], context.task_input)


def _seed_repo(repo_root: Path) -> None:
    (repo_root / "target-project/docs").mkdir(parents=True, exist_ok=True)
    (repo_root / "target-project/backend/app").mkdir(parents=True, exist_ok=True)
    (repo_root / "target-project/backend/tests").mkdir(parents=True, exist_ok=True)
    (repo_root / "target-project/AGENTS.md").write_text(
        "- `backend/app/models.py`\n- `backend/app/repository.py`\n- `backend/app/service.py`\n",
        encoding="utf-8",
    )
    (repo_root / "target-project/docs/code-map.md").write_text(
        "- `backend/app/models.py`\n- `backend/app/repository.py`\n- `backend/app/service.py`\n- `backend/tests/test_service.py`\n",
        encoding="utf-8",
    )
    (repo_root / "target-project/backend/app/models.py").write_text(
        "class Todo: pass\n",
        encoding="utf-8",
    )
    (repo_root / "target-project/backend/app/repository.py").write_text(
        "def save():\n    return True\n",
        encoding="utf-8",
    )
    (repo_root / "target-project/backend/app/service.py").write_text(
        "def run():\n    return save()\n",
        encoding="utf-8",
    )
    (repo_root / "target-project/backend/tests/test_service.py").write_text(
        "def test_placeholder():\n    assert True\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
