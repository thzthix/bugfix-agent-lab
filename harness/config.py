from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
