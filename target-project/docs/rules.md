# Implementation Rules

## General

- Keep functions and components short and focused on one responsibility.
- Prefer explicit state transitions over clever implicit conversions.
- Keep naming consistent for the same domain concept across backend and frontend.
- Match the UI reference closely before adding extra styling flourishes.

## Backend

- Follow Python style conventions compatible with `PEP 8`.
- Keep formatting compatible with `ruff format`.
- Keep code quality compatible with `ruff check`.
- Write tests for `pytest`.
- `models.py` owns domain-level data shapes.
- `repository.py` owns persistence and reload behavior.
- `service.py` owns business rules and orchestration.
- Keep storage-specific field translation inside the repository layer.
- Keep the completed-state concept canonical and explicit.

## Frontend

- Use React with small presentational components.
- Keep component state shallow and derive display state from API data when possible.
- Centralize visual tokens in CSS custom properties.
- Prefer semantic buttons and inputs over non-interactive wrappers.
- Keep layout responsive, but preserve the mobile-card composition from the reference image.

## Tests

- Tests are the source of truth for task success.
- Prefer fixes that preserve or clarify the intent of the tests.
- Do not weaken assertions to make a failing implementation pass.
