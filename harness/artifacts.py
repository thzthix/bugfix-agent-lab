import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class RetryContext:
    attempt: int
    max_attempts: int
    test_command: str
    modified_files: list[str]
    test_summary: str
    failure_excerpt: str


def build_retry_context(
    response: Any,
    attempt: int,
    max_attempts: int,
) -> RetryContext | None:
    apply_patch_output = _last_function_response(response, "apply_patch")
    run_tests_output = _last_function_response(response, "run_tests")
    if not isinstance(run_tests_output, dict):
        return None

    modified_files = []
    if isinstance(apply_patch_output, dict):
        candidate_files = apply_patch_output.get("modified_files", [])
        if isinstance(candidate_files, list):
            modified_files = [str(path) for path in candidate_files]

    test_command = str(run_tests_output.get("command", ""))
    test_summary = str(run_tests_output.get("summary", ""))
    failure_excerpt = _extract_failure_excerpt(run_tests_output)
    return RetryContext(
        attempt=attempt,
        max_attempts=max_attempts,
        test_command=test_command,
        modified_files=modified_files,
        test_summary=test_summary,
        failure_excerpt=failure_excerpt,
    )


def parse_final_output(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and start < end:
        try:
            parsed = json.loads(stripped[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return {
        "success": False,
        "summary": stripped or "Gemini did not return a structured result.",
        "modified_files": [],
        "report_markdown": stripped or "No report was returned.",
    }


def write_outputs(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(
        str(result.get("report_markdown", "")).strip(),
        encoding="utf-8",
    )


def _last_function_response(response: Any, name: str) -> dict[str, Any] | None:
    history = getattr(response, "automatic_function_calling_history", None) or []
    for content in reversed(history):
        parts = getattr(content, "parts", None) or []
        for part in parts:
            function_response = getattr(part, "function_response", None)
            if function_response is None:
                continue
            if getattr(function_response, "name", None) != name:
                continue
            payload = getattr(function_response, "response", None)
            if isinstance(payload, dict):
                return payload
    return None


def _extract_failure_excerpt(run_tests_output: dict[str, Any]) -> str:
    stderr = str(run_tests_output.get("stderr", "")).strip()
    stdout = str(run_tests_output.get("stdout", "")).strip()
    for text in (stderr, stdout):
        if not text:
            continue
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            return lines[-1]
    return str(run_tests_output.get("summary", "failed"))
