from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness.client import create_client
from harness.config import LoopConfig
from harness.loop import HarnessLoop


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the bug-fix harness loop.")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for the harness workspace.",
    )
    parser.add_argument(
        "--issue-file",
        help="Optional path to a text file containing the issue text.",
    )
    return parser.parse_args()


def read_issue_text(issue_file: str | None) -> str:
    if issue_file:
        return Path(issue_file).read_text(encoding="utf-8")

    issue_text = sys.stdin.read().strip()
    if not issue_text:
        raise ValueError("Issue text is required from --issue-file or stdin.")
    return issue_text


def main() -> int:
    args = parse_args()
    issue_text = read_issue_text(args.issue_file)

    client = create_client()
    config = LoopConfig(repo_root=Path(args.repo_root).resolve())
    loop = HarnessLoop(client=client, config=config)
    result = loop.run(issue_text)

    print(
        json.dumps(
            {
                "success": result.success,
                "attempts": result.attempts,
                "allowed_files": result.allowed_files,
                "final_response_id": result.final_response_id,
                "last_test_summary": result.last_test_summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
