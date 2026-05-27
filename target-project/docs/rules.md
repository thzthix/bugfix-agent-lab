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
- Prefer fixes that preserve or clarify the intent of the tests.
- Do not weaken assertions to make a failing implementation pass.

## Domain Consistency

- Represent the completed state with one clear domain concept and one canonical name.
- Keep the meaning of completion consistent across models, persistence, and service logic.
- Avoid parallel fields such as `done`, `completed`, and `is_completed` unless a mapping is explicitly required.

## Persistence Boundaries

- Keep storage-specific field translation inside the repository layer.
- Keep service logic independent from storage shape details when possible.
- Make state transitions explicit instead of relying on implicit truthy or falsy conversions.
