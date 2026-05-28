from __future__ import annotations


def build_instructions() -> str:
    return (
        "You are a coding agent working on a constrained bug-fix task.\n\n"
        "Goal:\n"
        "Fix the bug and make all tests pass.\n\n"
        "Constraints:\n"
        "Use only the provided tools.\n"
        "Modify only files that are explicitly allowed for the current task.\n\n"
        "Stop conditions:\n"
        "Finish when all tests pass.\n"
        "Fail if the tests still do not pass after 3 attempts.\n\n"
        "Final output:\n"
        "Return a structured report describing the error cause, attempted "
        "approaches, alternatives considered, chosen approach and why, the "
        "concrete changes made, and the final result."
    )
