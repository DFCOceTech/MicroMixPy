# Architecture — {{PROJECT_NAME}}

> Version: 1.0 | Status: Living Document | Last updated: {{DATE}}
> **Last Reconciled: {{DATE}}** — Review required if >30 days stale

## System Context

```
{{High-level context diagram showing external systems and actors}}
```

## Component Architecture

{{Description of major components, their responsibilities, and interactions}}

## Data Flows

### {{Flow Name}}
{{Describe the data flow step by step}}

## Execution Environment

{{Conda environment name, Python version, key library versions, hardware assumptions (RAM, GPU if needed), OS constraints}}

## Data Provenance & Reproducibility

{{Random seed strategy, data lineage (where raw data comes from and how it flows through the pipeline), version pinning approach, known numerical tolerance for floating-point comparisons}}

## Architectural Decision Records

### ADR-001: {{Decision Title}}
- **Status**: Accepted
- **Context**: {{What prompted this decision}}
- **Decision**: {{What was decided}}
- **Rationale**: {{Why}}
- **Consequences**: {{Trade-offs accepted}}
