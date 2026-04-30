# OpenSpec: Instructions for AI Agents

This document explains how AI agents should read, write, and maintain OpenSpec specification files. All agents in the harness must follow these conventions.

## What is OpenSpec?

OpenSpec is a lightweight specification format designed for AI-agent workflows. It provides a single source of truth for what a system should do (requirements), how to verify it (scenarios), and what has actually been built (implementation status). Every line of code traces back to a spec, and every spec traces forward to tests.

## Directory Structure

```
openspec/
  project.md              # Project-wide conventions (naming, coding standards)
  AGENTS.md               # This file -- instructions for AI agents
  capabilities/
    {capability-name}/
      spec.md             # Requirements and scenarios
      design.md           # Technical design (how to build it)
  change-proposals/
    {proposal-id}.md      # Proposed changes to existing specs
```

## Spec File Structure (spec.md)

Every capability has a `spec.md` with this structure:

```markdown
# Capability: {{Name}}

**Version**: {{semver}}
**Status**: Draft | Active | Deprecated
**Last Updated**: {{ISO date}}
**Owner**: {{agent or human}}

## Overview
{{Brief description of what this capability does}}

## Requirements

### REQ-{{CAP}}-{{NNN}}: {{Title}}
- **Priority**: MUST | SHOULD | MAY
- **Status**: SPECIFIED | IMPLEMENTED | PARTIALLY_IMPLEMENTED | DEFERRED
- **Description**: {{What the system must do}}
- **Rationale**: {{Why this requirement exists}}

## Scenarios

### SCENARIO-{{CAP}}-{{FLOW}}-{{NNN}}: {{Title}}
- **Priority**: CRITICAL | NORMAL
- **References**: REQ-{{CAP}}-{{NNN}}
- **Preconditions**: {{What must be true before this scenario}}

**Given** {{initial context}}
**When** {{action or event}}
**Then** {{expected outcome}}

## Implementation Status

| REQ ID | Status | Test Coverage | Notes |
|--------|--------|---------------|-------|
| REQ-{{CAP}}-001 | IMPLEMENTED | tests/test_{{cap}}.py | |

## Change History

| Date | Change | Rationale |
|------|--------|-----------|
| {{date}} | {{what changed}} | {{why}} |
```

## Naming Conventions

### Requirement IDs: REQ-{CAP}-{NNN}

- `{CAP}`: Short uppercase abbreviation for the capability (e.g., AUTH, DASH, SYNC)
- `{NNN}`: Three-digit sequential number, zero-padded (001, 002, ...)
- Examples: `REQ-AUTH-001`, `REQ-DASH-012`, `REQ-SYNC-003`

### Scenario IDs: SCENARIO-{CAP}-{FLOW}-{NNN}

- `{CAP}`: Same abbreviation as the capability
- `{FLOW}`: Short uppercase name for the user flow or feature area (e.g., LOGIN, EXPORT, FILTER)
- `{NNN}`: Three-digit sequential number
- Examples: `SCENARIO-AUTH-LOGIN-001`, `SCENARIO-DASH-FILTER-003`

### Design Decision IDs: ADR-{NNN}

- Sequential across the project
- Examples: `ADR-001`, `ADR-015`

### Story IDs: STORY-{EPIC}-{NNN}

- `{EPIC}`: Short uppercase abbreviation for the epic
- `{NNN}`: Three-digit sequential number
- Examples: `STORY-AUTH-001`, `STORY-ONBOARD-003`

## How to Read Specs (All Agents)

### Finding Relevant Specs
1. Check `openspec/capabilities/` for capability directories
2. Read the `spec.md` in each relevant capability directory
3. Use REQ-* IDs as stable references -- they do not change once assigned
4. Check Implementation Status to understand what is built vs. planned

### Understanding Priority
- **MUST** requirements: Non-negotiable. The system is broken without them.
- **SHOULD** requirements: Expected in a complete implementation. May be deferred with rationale.
- **MAY** requirements: Nice-to-have. Implement if time permits.

- **CRITICAL** scenarios: Must pass for a sprint to succeed. Zero tolerance for failure.
- **NORMAL** scenarios: Must pass at the configured threshold rate (typically 90%).

### Cross-referencing
- Every SCENARIO-* references one or more REQ-* items
- Every REQ-* should have at least one SCENARIO-* that tests it
- Stories reference the REQ-* items they implement
- Test files reference the SCENARIO-* items they verify

## How to Write Specs (Planner, Architect)

### Creating a New Capability Spec

1. Create directory: `openspec/capabilities/{capability-name}/`
2. Create `spec.md` following the structure above
3. Assign REQ-* IDs sequentially starting from 001
4. Write at least one SCENARIO-* for each REQ-*
5. Set all Implementation Status to SPECIFIED
6. Set spec status to Draft

### Rules for Writing Requirements

- **One requirement, one concern**: Do not combine "system shall authenticate users AND log all access attempts" into one REQ. Split them.
- **Testable**: A requirement must be verifiable. "System should be fast" is not testable. "System responds within 200ms for 95th percentile" is.
- **Unambiguous**: Avoid "should handle errors gracefully." Specify WHAT errors and WHAT handling.
- **Traced**: Every REQ must have a rationale connecting it to a user need or business goal.

### Rules for Writing Scenarios

- **Given/When/Then format**: Always. No exceptions.
- **Specific**: Include concrete values. For data scenarios: name the dataset, column, CRS, or parameter value. "Given the raw survey CSV at `data/raw/survey_2024.csv`" not "Given survey data."
- **Independent**: Each scenario should be verifiable without depending on other scenarios running first.
- **Complete**: Cover happy path, error paths, edge cases, and boundary conditions. For analyses: include out-of-range inputs, missing values, CRS mismatches.
- **Prioritized**: Mark scenarios that are essential for basic functionality as CRITICAL. Mark nice-to-have verifications as NORMAL.
- **Reproducibility**: SCENARIO-* for analyses MUST specify the random seed if randomness is involved.

### Modifying an Existing Spec

Never modify a published spec directly without a change proposal. The process:

1. Create `openspec/change-proposals/{CP-NNN}.md`:

```markdown
# Change Proposal: CP-{{NNN}}

**Date**: {{ISO date}}
**Author**: {{agent name}}
**Affects**: {{list of spec files}}
**Status**: Proposed | Accepted | Rejected

## Motivation
{{Why this change is needed}}

## Changes

### Modified Requirements
- REQ-{{CAP}}-{{NNN}}: {{current text}} -> {{proposed text}}
  - Rationale: {{why}}

### New Requirements
- REQ-{{CAP}}-{{NNN}}: {{proposed text}}
  - Rationale: {{why}}

### Removed Requirements
- REQ-{{CAP}}-{{NNN}}: {{current text}}
  - Rationale: {{why removing}}

### Modified Scenarios
{{Same pattern as requirements}}

### New Scenarios
{{Same pattern}}

## Impact Analysis
- Code changes required: {{list affected files/components}}
- Test changes required: {{list affected test files}}
- Other specs affected: {{list}}
```

2. Apply the changes to the spec after the change proposal is accepted (by the harness or user)

**Exception**: The Generator may update Implementation Status directly without a change proposal, since this reflects reality, not a change in intent.

## The Reconciliation Protocol

Specs and code must always agree. When they diverge:

### Code Diverges from Spec (Generator finds spec is wrong or impractical)

1. Implement what actually works
2. Update the spec to match the implementation
3. Add a Change History entry with rationale: "Implementation revealed that X was not feasible because Y. Updated to Z."
4. Flag in the handoff file so the Evaluator knows

### Spec Diverges from Code (Evaluator finds code does not match spec)

1. The Evaluator flags this as a spec fidelity issue
2. The Generator must either:
   a. Fix the code to match the spec, OR
   b. Update the spec with a rationale explaining why the code is correct
3. Option (b) requires a change proposal for non-trivial divergences

### The Cardinal Rule

**Never leave specs and code disagreeing silently.** If they disagree, someone must explicitly reconcile them with documented rationale. Silent divergence is the number one failure mode of spec-anchored development.

## Traceability Chain

The full traceability chain is:

```
User Need / Research Question
  -> PRD (product-brief.md, prd.md)
    -> REQ-* (spec.md)
      -> SCENARIO-* (spec.md)
        -> Story (epics/stories/)
          -> Test (tests/) or Notebook Cell (notebooks/)
            -> Implementation (src/ or notebooks/)
              -> Output Artifact (data/processed/, figures/)
                -> Implementation Status (spec.md)
```

Every link in this chain should be navigable in both directions. If you cannot trace a piece of code back to a REQ-*, or a REQ-* forward to a test, the chain is broken and must be repaired.

## Quick Reference for Each Agent

| Agent | Reads Specs? | Writes Specs? | Key Action |
|-------|-------------|---------------|------------|
| Discovery | Yes (for context) | No | Understands existing capabilities |
| Planner | Yes | Yes (new specs, change proposals) | Creates REQ-* and SCENARIO-* |
| Architect | Yes | Yes (design.md only) | Designs how to implement REQ-* |
| Design | Yes (for context) | No | Uses SCENARIO-* to define UX flows |
| Generator | Yes | Yes (Implementation Status only) | Implements REQ-*, tests SCENARIO-* |
| Evaluator | Yes | No (writes evaluations, not specs) | Verifies SCENARIO-*, checks fidelity |
