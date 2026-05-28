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
