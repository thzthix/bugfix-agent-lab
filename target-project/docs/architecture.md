# Architecture Overview

The target project is a small Python todo application designed for bug-fix agent exercises.

## Goals

- Reproduce realistic application bugs in a constrained codebase.
- Keep business logic small enough for iterative repair.
- Separate concerns clearly enough for multi-file debugging and repair.

## Planned Layers

- Domain layer
  Todo state and core data structures.
- Repository layer
  Read and write behavior for persisted todo data.
- Service layer
  Application rules and state transitions used by callers.

## Validation Model

- Tests define the expected behavior.
- The bug-fix loop should use failing tests as the primary signal for repair.
- The implementation should prefer small, explicit fixes over broad rewrites.

## Relationship to the Harness

This directory is the repair target.
The external harness is responsible for:

- invoking the model,
- exposing read/apply/test tools,
- enforcing access boundaries,
- capturing structured results and reports.
