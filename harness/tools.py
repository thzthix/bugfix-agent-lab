import json
import subprocess
import tempfile
from pathlib import Path

from google.genai import types

from harness.tool_utils import extract_patch_files, is_allowed_read_path


def read_file_impl(repo_root: Path, path: str) -> str:
    if not is_allowed_read_path(path):
        raise ValueError(f"Read path is not allowed: {path}")
    file_path = repo_root / path
    return file_path.read_text(encoding="utf-8")


def apply_patch_impl(
    repo_root: Path,
    patch: str,
    allowed_files: list[str] | None = None,
) -> str:
    touched_files = extract_patch_files(patch)
    if not touched_files:
        raise ValueError("Patch does not reference any files.")
    if allowed_files is not None:
        disallowed_files = [path for path in touched_files if path not in allowed_files]
        if disallowed_files:
            raise ValueError(
                f"Patch touches files outside the allowlist: {disallowed_files}"
            )
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".patch",
        delete=False,
    ) as patch_file:
        patch_file.write(patch)
        patch_path = Path(patch_file.name)

    try:
        dry_run = subprocess.run(
            ["git", "apply", "--check", "--unidiff-zero", str(patch_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if dry_run.returncode != 0:
            reason = dry_run.stderr.strip() or dry_run.stdout.strip() or "git apply --check failed."
            raise ValueError(reason)

        apply_result = subprocess.run(
            ["git", "apply", "--unidiff-zero", str(patch_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if apply_result.returncode != 0:
            reason = apply_result.stderr.strip() or apply_result.stdout.strip() or "git apply failed."
            raise ValueError(reason)
    finally:
        patch_path.unlink(missing_ok=True)

    result = {
        "success": True,
        "modified_files": touched_files,
        "summary": "Patch applied successfully.",
        "patch": patch,
    }
    return json.dumps(result, ensure_ascii=False)


def run_tests_impl(repo_root: Path, test_command: str) -> str:
    completed = subprocess.run(
        test_command,
        cwd=repo_root,
        shell=True,
        capture_output=True,
        text=True,
    )
    success = completed.returncode == 0
    result = {
        "success": success,
        "command": test_command,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "summary": "passed" if success else "failed",
    }
    return json.dumps(result, ensure_ascii=False)


def build_gemini_tool_config(
    repo_root: Path,
    test_command: str,
    allowed_files: list[str] | None = None,
) -> types.GenerateContentConfig:
    def read_file(path: str) -> str:
        """Read a text file from the workspace and return its contents."""
        return read_file_impl(repo_root, path)

    def apply_patch(patch: str) -> str:
        """Apply a patch proposal and return a JSON summary."""
        return apply_patch_impl(repo_root, patch, allowed_files)

    def run_tests() -> str:
        """Run the configured test command and return a JSON summary."""
        return run_tests_impl(repo_root, test_command)

    return types.GenerateContentConfig(tools=[read_file, apply_patch, run_tests])
