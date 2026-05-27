# Implementation Rules

## Style and Tooling

- Follow Python style conventions compatible with `PEP 8`.
- Keep formatting compatible with `ruff format`.
- Keep code quality compatible with `ruff check`.
- Write tests for `pytest`.

## Function Design

- Keep functions short and focused on one responsibility.
- Split validation, transformation, and persistence when they start to mix.
- Avoid deep conditional nesting when a helper function can simplify the flow.
- Avoid boolean flag parameters that change the meaning of a function.

## Module Responsibilities

- `models.py` defines domain objects and domain-level data shapes.
- `repository.py` handles persistence and reload behavior.
- `service.py` handles business logic and orchestration.

## Naming

- Use `snake_case` for functions and variables.
- Use clear boolean names such as `is_completed` or `has_items`.
- Do not introduce multiple names for the same domain concept without a clear reason.

## Tests

- Tests are the source of truth for task success.
- Do not modify test files during the exercise.
- Do not weaken assertions to make a failing implementation pass.

## Access Policy

- Read approved fix target files first.
- Read related test files and `pyproject.toml`.
- Read additional `src/**` files only when necessary to understand the failure.
- Keep the per-turn reading scope as small as possible.
- Start from direct evidence such as failing tests, stack traces, and approved fix candidates.
- Expand to additional source files only when the current evidence is insufficient.
- Concrete file-count and read-size limits are enforced by the harness.
- Modify only explicitly approved source files for the current task.

## Exercise Constraints

- Do not modify `tests/**`.
- Do not modify `pyproject.toml`.
- Do not modify `docs/**`.
- Produce a structured JSON result and a human-readable Markdown report at the end of a run.
