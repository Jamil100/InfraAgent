---
description: "Run evaluation framework on InfraAgent agent outputs to measure quality."
---

# Run Evaluation

Evaluate InfraAgent agent output quality using the AI Toolkit evaluation framework.

## What to Evaluate

- **Consulting Agent**: Does the `RequirementsHandoff` accurately capture user intent?
- **CodeGen Agent**: Does generated Bicep/Terraform compile? Are AVM modules used? Are tags present?
- **Standards Agent**: Are findings accurate? What's the false positive rate?
- **Security Agent**: Are vulnerabilities correctly identified? Are remediations actionable?

## Evaluation Dataset

Create test cases in `backend/tests/eval/` with input-output pairs:

```json
[
  {
    "input": "I need a VNet with 3 subnets in West Europe",
    "expected_output": {
      "project_name": "contains a kebab-case name",
      "resources_needed": "contains Microsoft.Network/virtualNetworks",
      "azure_region": "westeurope"
    }
  }
]
```

## Steps

1. Open **AI Toolkit** sidebar → **Evaluation**
2. Select the agent to evaluate
3. Load or create the test dataset
4. Configure evaluation metrics:
   - **Completeness**: Does the output contain all expected fields?
   - **Correctness**: Does `bicep build` succeed on CodeGen output?
   - **Relevance**: Do review findings match known issues?
5. Run the evaluation
6. Review results in the Evaluation panel
7. Use **Tracing** to inspect individual agent turns for failures

## Metrics to Track

| Metric | Target | Agent |
|---|---|---|
| Requirements capture rate | > 90% | Consulting |
| Bicep compilation success | > 95% | CodeGen |
| AVM module usage | > 80% of resources | CodeGen |
| Finding accuracy | > 85% | Standards/Security |
| False positive rate | < 15% | Standards/Security |
