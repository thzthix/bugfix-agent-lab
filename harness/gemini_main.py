import argparse
import json
import sys
from pathlib import Path

from harness.artifacts import (
    build_retry_context,
    parse_final_output,
    write_outputs,
)
from harness.client import create_client, generate_content_with_backoff
from harness.config import (
    DEFAULT_API_RETRIES,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_TEST_COMMAND,
)
from harness.prompts import build_issue_prompt, build_retry_prompt
from harness.task import build_loop_context
from harness.tools import build_gemini_tool_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Gemini bug-fix harness with automatic function calling."
    )
    parser.add_argument("--prompt", help="Prompt to send to Gemini.")
    parser.add_argument(
        "--issue-file",
        help="Optional path to a text file containing issue text.",
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
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for result.json and report.md when using --issue-file.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=DEFAULT_MAX_ATTEMPTS,
        help="Maximum retry attempts after failed run_tests results.",
    )
    parser.add_argument(
        "--api-retries",
        type=int,
        default=DEFAULT_API_RETRIES,
        help="Maximum Gemini API retries when retryDelay is returned.",
    )
    return parser.parse_args()


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


def read_issue_text(issue_file: str) -> str:
    return Path(issue_file).read_text(encoding="utf-8")


def main() -> int:
    args = parse_args()
    client = create_client()
    repo_root = Path(args.repo_root).resolve()

    context = None
    if args.issue_file:
        issue_text = read_issue_text(args.issue_file)
        context = build_loop_context(issue_text, repo_root)
        prompt = build_issue_prompt(context.task_input)
        allowed_files = context.allowed_files
    else:
        prompt = read_prompt(args.prompt)
        allowed_files = None

    config = build_gemini_tool_config(
        repo_root=repo_root,
        test_command=args.test_command,
        allowed_files=allowed_files,
    )
    if context is None:
        response = generate_content_with_backoff(
            client,
            model=args.model,
            contents=prompt,
            config=config,
            max_retries=args.api_retries,
        )
        print(response.text)
        return 0

    result = None
    for attempt in range(1, args.max_attempts + 1):
        response = generate_content_with_backoff(
            client,
            model=args.model,
            contents=prompt,
            config=config,
            max_retries=args.api_retries,
        )
        result = parse_final_output(response.text or "")
        retry_context = build_retry_context(
            response=response,
            attempt=attempt,
            max_attempts=args.max_attempts,
        )
        if retry_context is None or retry_context.test_summary != "failed":
            break
        if attempt >= args.max_attempts:
            break
        prompt = build_retry_prompt(context.task_input, retry_context)

    result = result or {
        "success": False,
        "summary": "Gemini did not return a result.",
        "modified_files": [],
        "report_markdown": "No report was returned.",
    }
    output_dir = Path(args.output_dir).resolve()
    write_outputs(output_dir, result)
    print(
        json.dumps(
            {
                "success": result.get("success", False),
                "summary": result.get("summary", ""),
                "output_dir": str(output_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.get("success", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
