from __future__ import annotations

from pathlib import Path

from harness.allowlist import (
    build_task_input,
    extract_error_paths,
    load_text,
    resolve_allowed_files,
)
from harness.config import LoopContext


def build_loop_context(
    issue_text: str,
    repo_root: Path,
) -> LoopContext:
    code_map_text = load_text(repo_root / "target-project/docs/code-map.md")
    error_paths = extract_error_paths(issue_text)
    allowed_files = resolve_allowed_files(error_paths, code_map_text)
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
