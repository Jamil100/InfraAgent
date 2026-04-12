# ADR-007: Split Port Interfaces into Per-Port Files

**Date**: 2026-04-12
**Status**: Accepted
**Deciders**: Jamil AlBouhairi (E1), Architecture Review

## Context

Issue #4 (Define all port interfaces) was initially implemented with all 7 port ABCs and their dataclasses consolidated in a single file: `src/application/ports/ports.py`.

This became a problem when the parallel 4-track development structure was established:

- **Track 1 (E1)** — needs `ILLMCompletionPort`
- **Track 2 (E2)** — needs `IInfraProviderPort`, `IPolicyEnginePort`
- **Track 3 (E4)** — needs `ISourceControlPort`
- **Track 4 (E5)** — needs `ITemplateRegistryPort`, `ISubscriptionDiscoveryPort`

All 4 engineers would be reading and potentially modifying the same `ports.py` file simultaneously. Any upstream change to the port contracts (a common occurrence early in a project) would produce a merge conflict that blocks all 4 tracks at once — the exact scenario the parallel structure is designed to avoid.

A secondary gap was also found: `IPolicyEnginePort` was missing the `check_avm_availability()` method specified in TechSpec Section 2.1, required by the Standards Agent (#27) and Validation Pipeline (#24).

## Decision

### 1. One file per port interface

Split `ports.py` into 7 dedicated modules, one per port:

| File | Port | Dataclasses |
|------|------|-------------|
| `llm_port.py` | `ILLMCompletionPort` | `LLMMessage`, `LLMResponse`, `ToolDefinition`, `TaskProfile` |
| `infra_provider_port.py` | `IInfraProviderPort` | `ValidationResult`, `PlanResult`, `ApplyResult` |
| `source_control_port.py` | `ISourceControlPort` | `PRResult`, `PipelineStatus` |
| `policy_engine_port.py` | `IPolicyEnginePort` | `PolicyViolation`, `PolicyResult` |
| `template_registry_port.py` | `ITemplateRegistryPort` | `TemplateMetadata`, `HydratedTemplate` |
| `observability_port.py` | `IObservabilityPort` | — |
| `subscription_discovery_port.py` | `ISubscriptionDiscoveryPort` | `DiscoveredResource`, `DiscoveredVNet`, `SubscriptionContext` |

### 2. Retain `ports.py` as a backward-compat re-export shim

Rather than deleting `ports.py`, it is rewritten to re-export all symbols from the individual files. This means:

- Any existing code using `from src.application.ports.ports import X` continues to work without change.
- The legacy ports (`ICodeGenPort`, `IValidationPort`, `IStandardsPort`, `ISecurityPort`, `IDeployPort`) that depend on domain models stay in `ports.py` since they pre-date the clean port split.

### 3. Add `check_avm_availability()` to `IPolicyEnginePort`

The method was specified in TechSpec Section 2.1 but omitted in the initial implementation. It is added to `policy_engine_port.py` with signature:

```python
async def check_avm_availability(
    self, resource_type: str, version: str | None = None
) -> bool: ...
```

This method is consumed by the Standards Agent (#27) to prefer AVM module usage over raw resource declarations, and by the Validation Pipeline (#24) for compliance checks.

## Alternatives Considered

### A. Keep everything in `ports.py`, use locking discipline (rejected)

Requiring engineers to coordinate before touching `ports.py` is a social contract, not a structural guarantee. Under time pressure (3-week sprint), this will be violated.

### B. Split by track rather than by port (rejected)

Grouping ports by which engineer owns them (e.g., `e1_ports.py`, `e2_ports.py`) would work short-term but produces nonsensical module names that outlive the sprint structure. Port names should reflect their domain, not their assignee.

### C. Generate ports from a schema/config file (rejected)

Over-engineered for 7 interfaces. The split itself achieves the isolation goal at zero tooling cost.

**Chosen: One file per port** ✓

## Consequences

### Positive

- **Merge conflict isolation:** Each track owns its port file. Changes to `ILLMCompletionPort` don't touch the file that contains `ISourceControlPort`.
- **Clearer ownership:** `policy_engine_port.py` is unambiguously E2's concern; `source_control_port.py` is E4's.
- **TechSpec alignment:** Issue #4 acceptance criteria explicitly lists per-port filenames — the implementation now matches the spec.
- **`check_avm_availability()` unblocks:** Standards Agent (#27) and Validation Pipeline (#24) can now implement against the complete interface.
- **Zero breaking changes:** `ports.py` shim preserves all existing import paths.

### Negative

- **More files to navigate:** 7 files instead of 1. Mitigated by `__init__.py` re-exporting all symbols so callers can always use `from src.application.ports import X`.
- **Shim indirection:** `ports.py` is now a layer of indirection. Mitigated by clear docstring explaining its purpose.

## Related Decisions

- **ADR-003 (Clean Architecture):** Port split operationalizes the architecture's dependency rule — each layer has a clear, narrow boundary.
- **ADR-006 (Unified IaC Provider):** `IInfraProviderPort` in `infra_provider_port.py` is the interface that decision implements.
- **Issue #4 (Port Interfaces):** This ADR documents the corrective revision to reach full acceptance criteria.

## Implementation Notes

- New canonical imports: `from src.application.ports.policy_engine_port import IPolicyEnginePort`
- Backward-compat imports still work: `from src.application.ports.ports import IPolicyEnginePort`
- Package-level imports also work: `from src.application.ports import IPolicyEnginePort`
- `check_avm_availability()` default `version=None` means "any version available"
