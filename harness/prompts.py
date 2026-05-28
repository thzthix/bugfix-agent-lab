from harness.artifacts import RetryContext


def build_issue_prompt(task_input: str) -> str:
    return (
        f"{task_input}\n\n"
        "When you are finished, output only valid JSON with the following keys:\n"
        "- success: boolean\n"
        "- summary: short string\n"
        "- modified_files: array of file paths\n"
        "- report_markdown: markdown string\n\n"
        "The report_markdown must include these sections:\n"
        "- Error Cause\n"
        "- Attempted Approaches\n"
        "- Chosen Approach\n"
        "- Work Performed\n"
        "- Result\n"
    )


def build_retry_prompt(task_input: str, retry_context: RetryContext) -> str:
    modified_files = "\n".join(
        f"  - {path}" for path in retry_context.modified_files
    ) or "  - (none)"
    return (
        f"{task_input}\n\n"
        "Previous attempt result:\n"
        f"- Attempt: {retry_context.attempt} of {retry_context.max_attempts}\n"
        "- Modified files:\n"
        f"{modified_files}\n"
        "- Test command:\n"
        f"  {retry_context.test_command}\n"
        "- Test summary:\n"
        f"  {retry_context.test_summary}\n"
        "- Failure details:\n"
        f"  {retry_context.failure_excerpt}\n\n"
        "Revise the fix based on the failure above.\n"
        "Keep the allowed file constraints.\n"
        "When finished, return only valid JSON.\n"
    )
