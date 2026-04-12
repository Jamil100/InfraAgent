# ADR-006: Unified IaC Provider Port with Terraform Adapter

**Date**: 2026-04-12
**Status**: Accepted
**Deciders**: Jamil AlBouhairi (E2), Architecture Review

## Context

Issue #4 introduced a unified `IInfraProviderPort` interface that abstracts both Terraform and Bicep operations (format, validate, lint, plan, apply). This unifies what were previously split across `IDeployPort` (plan/apply) and `IValidationPort` (format/validate) legacy interfaces.

Issue #13 requires implementing the first adapter: `TerraformInfraProviderAdapter`. Several architectural decisions were needed:

1. **Plan file storage:** How to couple `plan()` and `apply()` operations across async calls?
2. **Optional tooling:** Should linting fail if tflint is not installed, or gracefully degrade?
3. **Variable format:** How to pass Terraform variables through the port boundary?
4. **Input/output types:** Should ports use domain models (Pydantic) or language-agnostic dataclasses?

## Decision

### 1. Plan File Storage: UUID-Based Temp Directories

**Chosen approach:** Store Terraform plan files in system temp directory with UUID-based subdirectories. The UUID becomes the `plan_id` returned to callers. The adapter maintains an in-memory mapping of `plan_id -> temp_dir` for the lifetime of the adapter instance.

**Rationale:**
- **Stateless within pipeline execution:** Plan files are short-lived (within a single pipeline run), so ephemeral storage is appropriate
- **Resilient cleanup:** Uses system temp directory with automatic OS-level cleanup
- **Simple coupling:** `plan()` stores; `apply(plan_id)` retrieves. No external dependencies (Redis, database)
- **Clear semantics:** UUID acts as an opaque handle, clients don't need to know about filesystem details
- **Single-pipeline guarantee:** Within a pipeline execution, adapter instance is reused, so in-memory mapping is safe

**Consequence:** Plan files are lost on process restart (acceptable for MVP; can upgrade to persistent storage later)

### 2. tflint Requirement: Optional (Stretch Goal)

**Chosen approach:** `lint()` method attempts to run tflint. If not installed (FileNotFoundError), returns `ValidationResult(valid=True, warnings=["tflint not installed..."])` instead of failing.

**Rationale:**
- **Issue #13 marks lint as stretch goal** — indicates non-critical, best-effort
- **Graceful degradation:** Not all CI/CD environments have tflint installed
- **Non-blocking:** Lint failures should not block the pipeline from proceeding to plan/apply
- **Production-safe:** Allows deployment in environments where only Terraform CLI is available
- **Extensible:** Future adapters (Bicep) can have different lint tool requirements

**Consequence:** Lint quality checks may be skipped in some environments; compensated by IaC provider's built-in validation in the `validate()` step

### 3. Variable Format: JSON-Based terraform.tfvars

**Chosen approach:** Generate `terraform.tfvars` using JSON encoding with Terraform's `jsonDecode()` function:
```hcl
variable_name = jsonDecode('{"nested": "value"}')
another_var = jsonDecode('[1, 2, 3]')
```

**Rationale:**
- **No external dependencies:** Uses only Python's `json` module (stdlib)
- **Type-safe:** JSON serialization handles booleans, numbers, arrays, objects correctly
- **Language-agnostic:** Works for both Terraform and future Bicep adapter (which will use different variable syntax)
- **Simple implementation:** `json.dumps(value)` for any Python value
- **Terraform native:** Terraform's `jsonDecode()` is designed for exactly this use case

**Consequence:** Requires Terraform >= 0.12 (when jsonDecode was introduced); acceptable for modern projects

### 4. Input/Output Type Separation: Dataclass Ports vs Pydantic Domain

**Chosen approach:**
- **Port boundary:** Use dataclasses defined in `src/application/ports/ports.py` (ValidationResult, PlanResult, ApplyResult)
- **Adapter internals:** Adapter can use Pydantic models or raw data structures internally
- **Input files:** Accept generic `list[dict]` with `{"path", "content"}` instead of Pydantic `GeneratedFile` model

**Rationale:**
- **Clean separation of concerns:** Ports define canonical contracts independent of domain models
- **Type safety with flexibility:** Dataclasses provide structure without coupling to domain layer
- **Backward compatible:** Existing domain models (in `src/domain/models/`) remain unchanged
- **Adapter freedom:** Each adapter can use appropriate internal representations (subprocess output, streaming JSON, etc.)
- **Matches TechSpec:** Section 2.1 explicitly specifies dataclasses for port contracts

**Consequence:** Adapters must convert between dataclass outputs (port boundary) and Pydantic models (if they need them internally); small conversion overhead, large architectural benefit

## Alternatives Considered

### Plan Storage Alternatives

**A. Share filesystem path directly (rejected)**
- Callers would need to know the plan file location
- Security risk: callers could modify plan between plan() and apply()
- Not portable: Windows vs Unix path conventions

**B. In-memory dict without cleanup (rejected)**
- Plan files accumulate in memory if apply() never called
- Memory leak risk in long-running pipelines
- No cleanup story

**C. Persistent state backend (Redis/CosmosDB) (rejected for MVP)**
- Over-engineered for MVP with single-pipeline execution model
- Adds infrastructure dependency
- Can be added later (ADR amendment) without changing port interface

**Chosen: UUID-based temp dirs** ✓

### tflint Alternatives

**A. Required, fail if not installed (rejected)**
- Blocks pipelines in minimal environments
- Goes against "stretch goal" designation

**B. Completely skip, no lint output (rejected)**
- Inconsistent: some adapters lint, others don't
- Users don't know if linting was skipped or passed

**Chosen: Optional with warning** ✓

### Variable Format Alternatives

**A. HCL library (hcl2 package) (rejected)**
- Adds external dependency
- Overkill for simple key-value variables
- Harder to maintain

**B. Raw Python dict repr (rejected)**
- Not valid HCL/Terraform syntax
- Type conversion issues (Python bool vs HCL bool)

**Chosen: JSON-based with jsonDecode()** ✓

### Type Separation Alternatives

**A. Use Pydantic models everywhere (rejected)**
- Couples ports to domain layer
- Breaks adapter independence
- Violates Clean Architecture principles

**B. Use raw dicts everywhere (rejected)**
- Loss of type safety at port boundary
- Harder to test and debug
- No IDE autocomplete

**Chosen: Dataclasses at boundary, Pydantic internally** ✓

## Consequences

### Positive

- **Port independence:** IInfraProviderPort is pure, not tied to Pydantic or any domain models
- **Graceful tooling:** tflint absence doesn't break pipelines; Terraform validation is still enforced
- **Simple plan coupling:** UUID handles are opaque, clients don't need filesystem knowledge
- **Type-safe data transfer:** Dataclasses provide structure and IDE support
- **Extensible:** Plan/apply pattern works for Bicep adapter (Issue #15) without modification

### Negative

- **Ephemeral plans:** Process restart loses pending plans (mitigated: add persistent storage in ADR amendment if needed)
- **Json-based vars:** Slightly verbose terraform.tfvars (mitigated: standard Terraform pattern, well-understood)
- **Type conversion overhead:** Adapters must convert between dataclass ↔ internal representations (minimal, negligible performance impact)

### Mitigated By

- MVP scope: Single-pipeline execution is the current use case; persistent plan storage can be added later without breaking changes
- Clear error messages: When Terraform CLI or tflint is missing, error messages guide users to install them
- Backward compatibility: Existing domain models unchanged; only new port layer is added

## Related Decisions

- **ADR-003 (Clean Architecture):** This decision operationalizes clean architecture at the port boundary
- **Issue #4 (Port Interfaces):** Defines the IInfraProviderPort interface that this adapter implements
- **Future ADR (Persistent Plan Storage):** May be needed if multi-step pipelines require plan persistence across restarts

## Implementation Notes

- `TerraformInfraProviderAdapter` in `src/infrastructure/adapters/terraform_adapter.py`
- Plan storage uses `Path(tempfile.gettempdir()) / f"tf_plan_{uuid.uuid4()}"`
- tflint graceful failure in `lint()` method with FileNotFoundError catch
- JSON-based tfvars in `_write_tfvars()` helper method
- All public methods return dataclass instances from `src/application/ports.ports`
