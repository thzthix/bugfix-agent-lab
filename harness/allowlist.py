from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ALLOWED_PREFIXES = ("target-project/backend/app/",)
DEFAULT_FALLBACK_FILES = (
    "target-project/backend/app/models.py",
    "target-project/backend/app/repository.py",
    "target-project/backend/app/service.py",
)
DEFAULT_RELEVANT_TESTS = (
    "target-project/backend/tests/test_service.py",
    "target-project/backend/tests/test_api.py",
)

PATH_PATTERN = re.compile(
    r"((?:target-project/)?[A-Za-z0-9_./-]+\.(?:py|tsx|ts|js|jsx|md|json|toml))"
)


class AllowlistResolutionError(ValueError):
    """Raised when no allowed files can be resolved for a task."""


@dataclass
class TaskInput:
    error_summary: str
    allowed_files: list[str]
    relevant_tests: list[str]

    def render(self) -> str:
        allowed_lines = "\n".join(f"- {path}" for path in self.allowed_files)
        test_lines = "\n".join(f"- {path}" for path in self.relevant_tests)
        return (
            "Current task:\n"
            f"{self.error_summary.strip()}\n\n"
            "Allowed files for this task:\n"
            f"{allowed_lines}\n\n"
            "Relevant tests:\n"
            f"{test_lines}\n\n"
            "Use the test tool results as the source of truth. "
            "Fix the bug and make the tests pass."
        )


def extract_error_paths(issue_text: str) -> list[str]:
    return _extract_paths(issue_text)


def extract_error_summary(issue_text: str) -> str:
    stripped_lines = [line.strip() for line in issue_text.splitlines() if line.strip()]
    if not stripped_lines:
        return "The current task contains a failing issue that must be fixed."

    priority_markers = (
        "assertionerror",
        "traceback",
        "error:",
        "exception:",
        "failed:",
        "current failure:",
        "bug:",
    )
    for line in stripped_lines:
        lowered = line.lower()
        if any(marker in lowered for marker in priority_markers):
            return _clean_summary_line(line)

    return _clean_summary_line(stripped_lines[0])


def resolve_allowed_files(
    error_paths: list[str],
    code_map_text: str,
    allowed_prefixes: tuple[str, ...] = DEFAULT_ALLOWED_PREFIXES,
) -> list[str]:
    mapped_paths = _match_paths_from_code_map(error_paths, code_map_text)
    fallback_paths = list(DEFAULT_FALLBACK_FILES)
    directly_allowed_paths = [
        path for path in error_paths if _is_allowed_path(path, allowed_prefixes)
    ]
    can_use_fallback = bool(directly_allowed_paths or mapped_paths)
    prioritized_candidates = _order_by_fallback_priority(
        _dedupe_preserving_order([*mapped_paths, *fallback_paths]),
        fallback_paths,
    )
    combined_paths = _dedupe_preserving_order(
        [
            *directly_allowed_paths,
            *(prioritized_candidates if can_use_fallback else []),
        ]
    )
    allowed_files = _dedupe_preserving_order(
        [path for path in combined_paths if _is_allowed_path(path, allowed_prefixes)]
    )
    if not allowed_files:
        raise AllowlistResolutionError(
            "No allowed files could be resolved from the issue and project rules."
        )
    return allowed_files


def build_task_input(
    issue_text: str,
    allowed_files: list[str],
    relevant_tests: list[str] | None = None,
) -> str:
    tests = list(relevant_tests or DEFAULT_RELEVANT_TESTS)
    task_input = TaskInput(
        error_summary=extract_error_summary(issue_text),
        allowed_files=allowed_files,
        relevant_tests=tests,
    )
    return task_input.render()


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _match_paths_from_code_map(error_paths: list[str], code_map_text: str) -> list[str]:
    code_map_paths = _extract_paths(code_map_text)
    if not error_paths:
        return []

    matched_paths: list[str] = []
    for error_path in error_paths:
        error_name = Path(error_path).name
        error_stem = Path(error_path).stem
        for candidate in code_map_paths:
            candidate_name = Path(candidate).name
            candidate_stem = Path(candidate).stem
            if candidate in error_paths:
                continue
            if error_name == candidate_name or error_stem == candidate_stem:
                matched_paths.append(candidate)
                continue
            if "test_" in error_name and candidate_stem in error_stem:
                matched_paths.append(candidate)
    return _dedupe_preserving_order(matched_paths)


def _extract_paths(text: str) -> list[str]:
    raw_paths = [
        match if match.startswith("target-project/") else f"target-project/{match}"
        for match in PATH_PATTERN.findall(text.replace("`", ""))
    ]
    normalized_paths = [
        path.replace("target-project/target-project/", "target-project/")
        for path in raw_paths
    ]
    return _dedupe_preserving_order(normalized_paths)


def _is_allowed_path(path: str, allowed_prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(prefix) for prefix in allowed_prefixes)


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _clean_summary_line(line: str) -> str:
    return line.strip("`-• ").strip()


def _order_by_fallback_priority(
    values: list[str],
    fallback_paths: list[str],
) -> list[str]:
    priority = {path: index for index, path in enumerate(fallback_paths)}
    return sorted(values, key=lambda path: priority.get(path, len(priority)))
