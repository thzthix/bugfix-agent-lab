# Architecture Overview

The target project is a small full-stack grocery list application designed for
bug-fix agent exercises.

## Goals

- Reproduce realistic application bugs in a constrained codebase.
- Keep the bug surface narrow enough for iterative repair.
- Separate concerns clearly enough for multi-file debugging and repair.
- Provide a realistic UI consumer so backend state bugs are visible end-to-end.

## Planned Layers

### Frontend

- React application that renders the grocery list reference UI.
- Fetches todos and summary information from the backend API.
- Sends toggle and favorite actions back to the API.
- Can fall back to local demo data and `localStorage` for static GitHub Pages preview builds.

### Backend

- FastAPI application that exposes todo endpoints.
- Service layer owns list behavior and state transitions.
- Repository layer owns JSON persistence and reload behavior.

## Validation Model

- Backend tests define the first exercise's expected behavior.
- The bug-fix loop should use failing tests as the primary signal for repair.
- The implementation should prefer small, explicit fixes over broad rewrites.

## Relationship to the Harness

This directory is the repair target.
The external harness is responsible for:

- invoking the model,
- exposing read/apply/test tools,
- enforcing access boundaries,
- capturing structured results and reports.

## Deployment Note

- GitHub Pages is suitable for the static frontend preview.
- The FastAPI backend remains a separate runtime target and is not deployed on
  GitHub Pages.
