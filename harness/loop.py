from __future__ import annotations

import json
import subprocess
from typing import Any, Callable

from harness.config import (
    HarnessLoopError,
    LoopConfig,
    LoopContext,
    LoopResult,
    ToolExecutionResult,
)
from harness.decisions import handle_test_result
from harness.response_api import build_instructions
from harness.task import build_loop_context
from harness.tools import build_tools, extract_tool_calls
from harness.tool_utils import (
    default_apply_patch,
    extract_patch_files,
    is_allowed_read_path,
)


class HarnessLoop:
    def __init__(
        self,
        client: Any,
        config: LoopConfig,
        apply_patch_fn: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self._client = client
        self._config = config
        self._apply_patch_fn = apply_patch_fn or default_apply_patch

    def run(self, issue_text: str) -> LoopResult:
        context = build_loop_context(issue_text, self._config.repo_root)
        previous_response_id: str | None = None
        attempts = 0
        tool_history: list[ToolExecutionResult] = []
        last_test_summary: str | None = None

        while attempts < self._config.max_attempts:
            response = self.start_response(
                context=context,
                previous_response_id=previous_response_id,
            )
            previous_response_id = getattr(response, "id", None)

            tool_calls = extract_tool_calls(response)
            if not tool_calls:
                success = last_test_summary == "passed"
                return self.finish_loop(
                    success=success,
                    attempts=attempts,
                    context=context,
                    previous_response_id=previous_response_id,
                    last_test_summary=last_test_summary,
                    tool_history=tool_history,
                )

            tool_execution_results, tool_response_inputs = self.execute_tool_calls(
                tool_calls,
                context,
            )
            tool_history.extend(tool_execution_results)

            decision = handle_test_result(tool_execution_results)

            previous_response_id = self.send_tool_outputs(
                previous_response_id,
                tool_response_inputs,
            )

            attempts, last_test_summary, loop_result = self._apply_decision(
                decision=decision,
                attempts=attempts,
                context=context,
                previous_response_id=previous_response_id,
                current_last_test_summary=last_test_summary,
                tool_history=tool_history,
            )
            if loop_result is not None:
                return loop_result

        return self.finish_loop(
            success=False,
            attempts=attempts,
            context=context,
            previous_response_id=previous_response_id,
            last_test_summary=last_test_summary,
            tool_history=tool_history,
        )

    def start_response(
        self,
        context: LoopContext,
        previous_response_id: str | None,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": self._config.model,
            "instructions": build_instructions(),
            "tools": build_tools(),
        }
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id
        else:
            kwargs["input"] = context.task_input
        return self._client.responses.create(**kwargs)

    def send_tool_outputs(
        self,
        previous_response_id: str | None,
        tool_response_inputs: list[dict[str, Any]],
    ) -> str | None:
        response = self._client.responses.create(
            model=self._config.model,
            previous_response_id=previous_response_id,
            input=tool_response_inputs,
            tools=build_tools(),
        )
        return getattr(response, "id", None)

    def _apply_decision(
        self,
        decision: str,
        attempts: int,
        context: LoopContext,
        previous_response_id: str | None,
        current_last_test_summary: str | None,
        tool_history: list[ToolExecutionResult],
    ) -> tuple[int, str | None, LoopResult | None]:
        if decision == "continue":
            return attempts, current_last_test_summary, None

        last_test_summary = decision
        if decision == "passed":
            attempts += 1
            return (
                attempts,
                last_test_summary,
                self.finish_loop(
                    success=True,
                    attempts=attempts,
                    context=context,
                    previous_response_id=previous_response_id,
                    last_test_summary=last_test_summary,
                    tool_history=tool_history,
                ),
            )

        if decision == "failed":
            return attempts + 1, last_test_summary, None

        raise HarnessLoopError(f"Unsupported loop decision: {decision}")

    def finish_loop(
        self,
        success: bool,
        attempts: int,
        context: LoopContext,
        previous_response_id: str | None,
        last_test_summary: str | None,
        tool_history: list[ToolExecutionResult],
    ) -> LoopResult:
        return LoopResult(
            success=success,
            attempts=attempts,
            allowed_files=context.allowed_files,
            final_response_id=previous_response_id,
            last_test_summary=last_test_summary,
            tool_history=tool_history,
        )

    def execute_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        context: LoopContext,
    ) -> tuple[list[ToolExecutionResult], list[dict[str, Any]]]:
        tool_execution_results: list[ToolExecutionResult] = []
        tool_response_inputs: list[dict[str, Any]] = []

        for tool_call in tool_calls:
            result = self._execute_single_tool_call(tool_call, context)
            tool_execution_results.append(result)
            tool_response_inputs.append(
                self._build_tool_response_input(tool_call, result)
            )

        return tool_execution_results, tool_response_inputs

    def _execute_single_tool_call(
        self,
        tool_call: dict[str, Any],
        context: LoopContext,
    ) -> ToolExecutionResult:
        name = tool_call["name"]
        arguments = tool_call["arguments"]
        if name == "read_file":
            return ToolExecutionResult(
                tool_name=name,
                output=self._read_file(
                    path=arguments["path"],
                    start_line=arguments.get("start_line"),
                    end_line=arguments.get("end_line"),
                ),
            )
        if name == "apply_patch":
            output = self._apply_patch(arguments["patch"], context.allowed_files)
            return ToolExecutionResult(tool_name=name, output=output)
        if name == "run_tests":
            return ToolExecutionResult(tool_name=name, output=self._run_tests())
        raise HarnessLoopError(f"Unsupported tool call: {name}")

    def _build_tool_response_input(
        self,
        tool_call: dict[str, Any],
        result: ToolExecutionResult,
    ) -> dict[str, Any]:
        return {
            "type": "function_call_output",
            "call_id": tool_call["call_id"],
            "output": json.dumps(result.output),
        }

    def _read_file(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> dict[str, Any]:
        if not is_allowed_read_path(path):
            raise HarnessLoopError(f"Read path is not allowed: {path}")
        file_path = self._config.repo_root / path
        lines = file_path.read_text(encoding="utf-8").splitlines()
        if start_line is None and end_line is None:
            content = "\n".join(lines)
            return {
                "path": path,
                "start_line": 1 if lines else None,
                "end_line": len(lines) if lines else None,
                "content": content,
            }

        start = max((start_line or 1) - 1, 0)
        stop = end_line or len(lines)
        sliced = lines[start:stop]
        return {
            "path": path,
            "start_line": start + 1,
            "end_line": start + len(sliced),
            "content": "\n".join(sliced),
        }

    def _apply_patch(
        self,
        patch_text: str,
        allowed_files: list[str],
    ) -> dict[str, Any]:
        touched_files = extract_patch_files(patch_text)
        if not touched_files:
            raise HarnessLoopError("Patch does not reference any files.")
        disallowed_files = [path for path in touched_files if path not in allowed_files]
        if disallowed_files:
            raise HarnessLoopError(
                f"Patch touches files outside the allowlist: {disallowed_files}"
            )
        return self._apply_patch_fn(patch_text)

    def _run_tests(self) -> dict[str, Any]:
        completed = subprocess.run(
            self._config.test_command,
            cwd=self._config.repo_root,
            shell=True,
            capture_output=True,
            text=True,
        )
        success = completed.returncode == 0
        summary = "passed" if success else "failed"
        return {
            "success": success,
            "command": self._config.test_command,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "summary": summary,
        }
