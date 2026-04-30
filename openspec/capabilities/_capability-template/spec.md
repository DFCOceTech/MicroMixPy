# {{Capability Name}} — Specification

> Version: 1.0 | Status: Draft | Last updated: {{DATE}}

## Purpose

{{What this capability / analysis / data product does and why it exists. Include the research question it answers or the data product it produces.}}

## Functional Requirements

### REQ-{{CAP}}-001: {{Requirement Title}}
The system SHALL {{requirement description}}.

### REQ-{{CAP}}-002: {{Requirement Title}}
The system SHALL {{requirement description}}.

## Acceptance Scenarios

### SCENARIO-{{CAP}}-001: {{Scenario Title}}
**GIVEN** {{precondition — e.g., the raw CSV at data/raw/X.csv with schema Y}}
**WHEN** {{action — e.g., the ingestion script is run with default parameters}}
**THEN** {{expected outcome — e.g., data/processed/X_clean.csv contains N rows, column Z has dtype float64, no nulls in required fields}}

### SCENARIO-{{CAP}}-002: {{Scenario Title}}
**GIVEN** {{precondition}}
**WHEN** {{action}}
**THEN** {{expected outcome}}

<!-- For analyses with randomness, add: -->
<!-- **SEED**: {{random seed value — required if THEN references stochastic outputs}} -->

## Data Contracts

<!-- For pipeline capabilities: describe inputs and outputs. -->

### Inputs
| Name | Path / Source | Format | Required Columns / Fields | CRS |
|------|--------------|--------|--------------------------|-----|
| {{Dataset}} | `data/raw/{{path}}` | {{CSV/GeoJSON/Shapefile/Raster}} | {{col1, col2}} | {{EPSG:XXXX or N/A}} |

### Outputs
| Name | Path | Format | Schema / Fields | CRS |
|------|------|--------|----------------|-----|
| {{Output}} | `data/processed/{{path}}` | {{CSV/GeoJSON/PNG}} | {{col1: dtype, col2: dtype}} | {{EPSG:XXXX or N/A}} |

## Implementation Status ({{DATE}})

<!-- MANDATORY: Update this section after implementation. -->

**Status**: Not Started | In Progress | Implemented | Partially Implemented | Reproducibility Verified

### What's Built
- {{List implemented requirements with file references (src/, notebooks/, scripts/)}}

### Reproducibility
- **Seed**: {{random seed value, or "not applicable"}}
- **Re-run verified**: {{yes / no / not yet}}
- **Known numerical tolerance**: {{e.g., ±0.001 for floating-point statistics, or "exact"}}

### Deviations from Spec
- {{List any intentional divergences with rationale}}

### Deferred
- {{List requirements not yet implemented with reason}}
