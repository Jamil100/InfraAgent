# ADR-005: Microsoft Agent Framework for Workflow Patterns

**Date**: 2026-04-10
**Status**: Accepted
**Deciders**: Hans Havlik

## Context

The InfraAgent pipeline is a deterministic, multi-stage workflow: Consulting → CodeGen → Review Loop → PR → Plan → Deploy. This is a graph-based flow with conditional loops and human gates — not a free-form LLM conversation.

Microsoft Agent Framework provides two patterns:
1. **Agents** (dynamic, LLM-driven) — for individual agent implementations
2. **Workflows** (graph-based, deterministic) — for orchestrating agents in a pipeline

## Decision

Use **Microsoft Agent Framework** (`agent-framework` Python package) for both individual agents and the pipeline orchestration. The `OrchestratorPipeline` in `pipeline.py` implements the Workflow pattern with explicit stage transitions.

## Consequences

- **Positive**: Graph-based orchestration with built-in checkpointing for long-running pipelines
- **Positive**: Human-in-the-loop support (H1/H2 gates) is a framework feature
- **Positive**: Unified SDK for both agent creation and workflow orchestration
- **Positive**: Strong Microsoft alignment (same SDK used by Foundry)
- **Negative**: Framework is in preview (`agent-framework-core==1.0.0rc3`) — API may change
- **Mitigated**: Pin dependency versions in `pyproject.toml`; current pipeline uses standard async patterns that would survive API changes
