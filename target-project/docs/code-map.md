# Code Map

This document is a lightweight index for the target project.

## Backend

- `backend/app/models.py`
  Domain models and API-facing data shapes for todo items.
- `backend/app/repository.py`
  JSON-backed persistence and reload behavior.
- `backend/app/service.py`
  Todo business logic such as create, toggle, favorite, filtering, and summaries.
- `backend/app/main.py`
  FastAPI routes used by the frontend.
- `backend/tests/test_service.py`
  Behavior verification for the first bug-fix exercise.

## Frontend

- `frontend/src/App.tsx`
  Page composition, data fetching, and optimistic interaction flow.
- `frontend/src/components/TodoRow.tsx`
  Row-level task rendering.
- `frontend/src/styles.css`
  Visual system and layout for the grocery-list UI.

## Exercise Focus

The first exercise focuses on completed-state toggle and persistence consistency.
The expected repair target is primarily in the backend, while the frontend acts
as a realistic consumer of the API contract.
