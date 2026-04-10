---
description: "Review generated IaC code against InfraAgent standards and security rules."
---

# Review IaC Code

Review the generated IaC code in the `infra/` directory (or the files specified) against InfraAgent's standards and security rules.

## Standards Checks

1. **Naming**: Resources follow `{env}-{project}-{type}` pattern
2. **Tags**: Every resource has `environment`, `project`, `managed-by` tags
3. **Modularity**: Each logical resource group is a separate module/file
4. **Parameters**: No hardcoded environment values — everything parameterized
5. **Outputs**: All resource IDs and key endpoints are in outputs

## Security Checks

1. **Public exposure**: Flag public IPs, open NSG rules (`0.0.0.0/0`), publicly accessible storage
2. **Encryption**: TLS 1.2+, encryption at rest, HTTPS-only
3. **Identity**: Managed identities preferred; flag shared keys or embedded credentials
4. **Secrets**: Must reference Key Vault, not inline
5. **Network security**: No `*` in NSG source/destination, no unrestricted port ranges
6. **Logging**: Recommend diagnostic settings where applicable

## Output Format

For each finding, report:
- **Severity**: error / warning / info
- **File**: Which file(s)
- **Issue**: What's wrong
- **Remediation**: How to fix it

Summarize with total error/warning/info counts.
