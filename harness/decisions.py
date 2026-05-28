from __future__ import annotations

from harness.config import ToolExecutionResult


def handle_test_result(
    tool_execution_results: list[ToolExecutionResult],
) -> str:
    for result in tool_execution_results:
        if result.tool_name != "run_tests":
            continue

        if result.output["success"]:
            return "passed"
        return "failed"

    return "continue"
