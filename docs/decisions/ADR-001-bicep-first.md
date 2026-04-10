# ADR-001: Bicep-First IaC Strategy

**Date**: 2026-04-10
**Status**: Accepted
**Deciders**: Hans Havlik

## Context

The PRD defines dual IaC support for both Terraform and Bicep. Supporting both from day one doubles CodeGen complexity (two file structures, two validation pipelines, two MCP servers, two sets of AVM modules).

The hackathon is judged by Microsoft executives. Bicep is Microsoft's native IaC language for Azure. Azure Verified Modules (AVM) provide production-ready Bicep modules aligned with the Well-Architected Framework.

The Bicep MCP Server added HTTP transport on April 8, 2026 — making it viable for remote MCP in Foundry-hosted agents.

## Decision

Implement **Bicep as the primary IaC language**. Terraform support is preserved in the architecture (via `IaCLanguage` enum and port abstractions) but deferred to post-MVP.

## Consequences

- **Positive**: Halved CodeGen complexity, strong Microsoft alignment for hackathon judging, AVM-first module strategy is native to Bicep
- **Positive**: No Terraform state management complexity for MVP
- **Negative**: Teams using Terraform-only environments can't use the MVP
- **Mitigated**: `IaCLanguage` enum and ports pattern make adding Terraform a plug-in exercise later
