from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_API_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 10.0
DEFAULT_TEST_COMMAND = (
    "python3 -m pytest target-project/backend/tests/test_service.py "
    "target-project/backend/tests/test_api.py"
)
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_ALLOWED_READ_PREFIXES = (
    "target-project/backend/",
    "target-project/docs/",
    "target-project/AGENTS.md",
)


@dataclass
class LoopContext:
    issue_text: str
    error_paths: list[str]
    allowed_files: list[str]
    task_input: str
    relevant_tests: list[str]
