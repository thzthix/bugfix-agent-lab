from __future__ import annotations

import json
from typing import Any


def build_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": "read_file",
            "description": (
                "Read a text file from the allowed workspace. "
                "Optionally read a line range."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to the repository root.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "1-based start line. Optional.",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "1-based end line. Optional.",
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "apply_patch",
            "description": (
                "Apply a patch string with before/after context. "
                "The harness rejects edits outside the task allowlist."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patch": {
                        "type": "string",
                        "description": "Patch text to apply.",
                    }
                },
                "required": ["patch"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "run_tests",
            "description": (
                "Run the fixed test command for this task and return stdout, stderr, "
                "and a short summary."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    ]


def extract_tool_calls(response: Any) -> list[dict[str, Any]]:
    output_items = getattr(response, "output", [])
    tool_calls: list[dict[str, Any]] = []
    for item in output_items:
        item_type = getattr(item, "type", None)
        if item_type != "function_call":
            continue
        arguments = getattr(item, "arguments", "{}")
        tool_calls.append(
            {
                "call_id": getattr(item, "call_id"),
                "name": getattr(item, "name"),
                "arguments": json.loads(arguments),
            }
        )
    return tool_calls
