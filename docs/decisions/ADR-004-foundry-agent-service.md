# ADR-004: Azure AI Foundry Agent Service as Orchestration Platform

**Date**: 2026-04-10
**Status**: Accepted
**Deciders**: Hans Havlik

## Context

Several platforms can host multi-agent AI systems: Azure AI Foundry Agent Service, Semantic Kernel, LangGraph, AutoGen, or custom orchestration.

The hackathon is a Microsoft partner event. Judges score "Platform Excellence & Proper Use of Microsoft Capabilities." Azure AI Foundry Agent Service provides hosted agents, thread management, ModelRouter, tracing, and evaluation — all Microsoft-native.

## Decision

Use **Azure AI Foundry Agent Service** via the `azure-ai-projects` Python SDK as the core orchestration platform. Agents are Foundry-hosted agents. Thread state is managed by Foundry. ModelRouter handles model selection.

## Consequences

- **Positive**: Maximum hackathon scoring on Microsoft platform alignment
- **Positive**: Built-in tracing (Foundry tracing) and evaluation (Foundry evaluations)
- **Positive**: ModelRouter eliminates hardcoded model names — agents declare task intent
- **Positive**: Thread management handled by Foundry (no custom conversation state)
- **Negative**: Foundry has constraints: max 5 replicas, 100s MCP timeout, Linux AMD64 only, no VNet
- **Negative**: MCP servers must be remote HTTP (not localhost) when deployed to Foundry
- **Mitigated**: For local dev, MCP servers run locally via `.vscode/mcp.json`; remote deployment uses Azure Container Apps
