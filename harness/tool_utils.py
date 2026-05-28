from __future__ import annotations

from harness.config import DEFAULT_ALLOWED_READ_PREFIXES


def extract_patch_files(patch_text: str) -> list[str]:
    files: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            files.append(line.removeprefix("+++ b/").strip())
    return list(dict.fromkeys(files))


def is_allowed_read_path(path: str) -> bool:
    return any(
        path == prefix.rstrip("/") or path.startswith(prefix)
        for prefix in DEFAULT_ALLOWED_READ_PREFIXES
    )


def default_apply_patch(patch_text: str) -> dict[str, object]:
    touched_files = extract_patch_files(patch_text)
    return {
        "success": True,
        "modified_files": touched_files,
        "summary": "Patch accepted by the harness apply function.",
        "patch": patch_text,
    }
