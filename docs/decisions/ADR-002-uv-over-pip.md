# ADR-002: uv Over pip for Dependency Management

**Date**: 2026-04-10
**Status**: Accepted
**Deciders**: Hans Havlik

## Context

The project needs a Python package manager. pip + venv is the standard but requires separate virtual environment management, lacks a lockfile by default, and is slow for large dependency trees.

uv is an extremely fast Python package manager written in Rust that handles virtual environment creation, dependency resolution, locking, and installation in a single tool.

## Decision

Use **uv** with `pyproject.toml` as the sole dependency management tool. No `requirements.txt`.

## Consequences

- **Positive**: Single command `uv sync` handles venv creation + dependency install
- **Positive**: Deterministic `uv.lock` lockfile for reproducible builds
- **Positive**: 10-100× faster than pip for cold installs
- **Negative**: Team members need to install uv (`astral.sh/uv/install`)
- **Negative**: Less familiar to developers who only know pip
- **Mitigated**: Setup guide covers uv installation; GitHub Actions uses `astral-sh/setup-uv@v4`
