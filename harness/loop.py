from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from harness.allowlist import (
    build_task_input,
    extract_error_paths,
    load_text,
    resolve_allowed_files,
)


DEFAULT_MODEL = "gpt-5.5"
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_TEST_COMMAND = (
    "python3 -m pytest target-project/backend/tests/test_service.py "
    "target-project/backend/tests/test_api.py"
)
DEFAULT_ALLOWED_READ_PREFIXES = (
    "target-project/backend/",
    "target-project/docs/",
    "target-project/AGENTS.md",
)


class HarnessLoopError(RuntimeError):
    """Raised when the harness loop cannot proceed."""


@dataclass
class LoopConfig:
    repo_root: Path
    model: str = DEFAULT_MODEL
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    test_command: str = DEFAULT_TEST_COMMAND


@dataclass
class LoopContext:
    issue_text: str
    error_paths: list[str]
    allowed_files: list[str]
    task_input: str
    relevant_tests: list[str]


@dataclass
class ToolExecutionResult:
    tool_name: str
    output: dict[str, Any]


@dataclass
class LoopResult:
    success: bool
    attempts: int
    allowed_files: list[str]
    final_response_id: str | None
    last_test_summary: str | None
    tool_history: list[ToolExecutionResult]


def build_loop_context(
    issue_text: str,
    repo_root: Path,
) -> LoopContext:
    code_map_text = load_text(repo_root / "target-project/docs/code-map.md")
    agents_text = load_text(repo_root / "target-project/AGENTS.md")
    error_paths = extract_error_paths(issue_text)
    allowed_files = resolve_allowed_files(error_paths, code_map_text, agents_text)
    task_input = build_task_input(issue_text, allowed_files)
    relevant_tests = [
        "target-project/backend/tests/test_service.py",
        "target-project/backend/tests/test_api.py",
    ]
    return LoopContext(
        issue_text=issue_text,
        error_paths=error_paths,
        allowed_files=allowed_files,
        task_input=task_input,
        relevant_tests=relevant_tests,
    )


def build_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": "read_file",
            "description": (
                "Read a text file from the allowed workspace. "
                "Optionally read a line range."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to the repository root.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "1-based start line. Optional.",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "1-based end line. Optional.",
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "apply_patch",
            "description": (
                "Apply a patch string with before/after context. "
                "The harness rejects edits outside the task allowlist."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patch": {
                        "type": "string",
                        "description": "Patch text to apply.",
                    }
                },
                "required": ["patch"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "run_tests",
            "description": (
                "Run the fixed test command for this task and return stdout, stderr, "
                "and a short summary."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    ]


def build_instructions() -> str:
    return (
        "You are a coding agent working on a constrained bug-fix task.\n\n"
        "Goal:\n"
        "Fix the bug and make all tests pass.\n\n"
        "Constraints:\n"
        "Use only the provided tools.\n"
        "Modify only files that are explicitly allowed for the current task.\n\n"
        "Stop conditions:\n"
        "Finish when all tests pass.\n"
        "Fail if the tests still do not pass after 3 attempts.\n\n"
        "Final output:\n"
        "Return a structured report describing the error cause, attempted "
        "approaches, alternatives considered, chosen approach and why, the "
        "concrete changes made, and the final result."
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
        self._apply_patch_fn = apply_patch_fn or _default_apply_patch

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
        if not _is_allowed_read_path(path):
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
        touched_files = _extract_patch_files(patch_text)
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


def extract_tool_calls(response: Any) -> list[dict[str, Any]]:
    output_items = getattr(response, "output", [])
    tool_calls: list[dict[str, Any]] = []
    for item in output_items:
        item_type = getattr(item, "type", None)
        if item_type != "function_call":
            continue
        arguments = getattr(item, "arguments", "{}")
        tool_calls.append(
            {
                "call_id": getattr(item, "call_id"),
                "name": getattr(item, "name"),
                "arguments": json.loads(arguments),
            }
        )
    return tool_calls


def _extract_patch_files(patch_text: str) -> list[str]:
    files: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            files.append(line.removeprefix("+++ b/").strip())
    return list(dict.fromkeys(files))


def _is_allowed_read_path(path: str) -> bool:
    return any(
        path == prefix.rstrip("/") or path.startswith(prefix)
        for prefix in DEFAULT_ALLOWED_READ_PREFIXES
    )


def _default_apply_patch(patch_text: str) -> dict[str, Any]:
    touched_files = _extract_patch_files(patch_text)
    return {
        "success": True,
        "modified_files": touched_files,
        "summary": "Patch accepted by the harness apply function.",
        "patch": patch_text,
    }
