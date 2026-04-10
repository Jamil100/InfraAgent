# ADR-003: Clean Architecture with Pragmatic Scope

**Date**: 2026-04-10
**Status**: Accepted
**Deciders**: Hans Havlik

## Context

The PRD specifies a full hexagonal / ports-and-adapters architecture. This is ideal for long-term maintainability but adds boilerplate for a hackathon where speed matters.

The team has 3 active developers and ~25 days until the May 5 submission deadline.

## Decision

Adopt **clean architecture at the boundary level** (ports for external integrations, domain models in core, adapters implement ports) but **don't over-abstract** internally. Specifically:

- Port interfaces (`ports.py`) for all external integrations
- Pydantic domain models in `core/models.py` (no ORM, no database layer for MVP)
- No repository pattern for MVP (in-memory session store)
- No dependency injection container — manual wiring in `routes.py`

## Consequences

- **Positive**: External dependencies are swappable (mock agents in tests, swap GitHub for ADO)
- **Positive**: Minimal boilerplate — fast to iterate
- **Positive**: Clean separation is visible to judges reviewing code quality
- **Negative**: In-memory session store means pipeline state is lost on restart
- **Mitigated**: Replace with Redis/Cosmos in a future iteration without touching the pipeline
