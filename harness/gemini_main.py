import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from harness.config import DEFAULT_TEST_COMMAND
from harness.tool_utils import default_apply_patch, is_allowed_read_path


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

def read_file_impl(repo_root: Path, path: str) -> str:
    if not is_allowed_read_path(path):
        raise ValueError(f"Read path is not allowed: {path}")
    file_path = repo_root / path
    return file_path.read_text(encoding="utf-8")


def apply_patch_impl(patch: str) -> str:
    result = default_apply_patch(patch)
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a minimal Gemini harness call with automatic function calling."
    )
    parser.add_argument(
        "--prompt",
        help="Prompt to send to Gemini.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_GEMINI_MODEL,
        help="Gemini model name.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for workspace tools.",
    )
    parser.add_argument(
        "--test-command",
        default=DEFAULT_TEST_COMMAND,
        help="Test command exposed to the run_tests tool.",
    )
    return parser.parse_args()


def create_gemini_client() -> genai.Client:
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=api_key)


def read_prompt(prompt: str | None) -> str:
    if prompt:
        return prompt

    stdin_text = sys.stdin.read().strip()
    if not stdin_text:
        return (
            "Use read_file on target-project/backend/app/repository.py and "
            "summarize what the save function does."
        )
    return stdin_text


def build_generate_content_config(
    repo_root: Path,
    test_command: str,
) -> types.GenerateContentConfig:
    def read_file(path: str) -> str:
        """Read a text file from the workspace and return its contents."""
        return read_file_impl(repo_root, path)

    def apply_patch(patch: str) -> str:
        """Apply a patch proposal and return a JSON summary."""
        return apply_patch_impl(patch)

    def run_tests() -> str:
        """Run the configured test command and return a JSON summary."""
        return run_tests_impl(repo_root, test_command)

    return types.GenerateContentConfig(
        tools=[read_file, apply_patch, run_tests]
    )


def main() -> int:
    args = parse_args()
    prompt = read_prompt(args.prompt)
    client = create_gemini_client()
    repo_root = Path(args.repo_root).resolve()
    config = build_generate_content_config(
        repo_root=repo_root,
        test_command=args.test_command,
    )
    response = client.models.generate_content(
        model=args.model,
        contents=prompt,
        config=config,
    )
    print(response.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
