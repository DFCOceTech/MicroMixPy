# Integrated BMAD + OpenSpec Workflow

> Version: 2.1 | Status: Living Document | Last updated: {{DATE}}

## Development Model: Spec-Anchored

This project uses **spec-anchored development** — the middle tier of Specification-Driven Development (SDD):

- **Specs are authoritative** for *what should be built* (requirements, behavior, acceptance criteria)
- **Code is authoritative** for *what is built* (implementation details, runtime behavior)
- **Reconciliation** bridges the two — specs and code are kept in agreement through explicit update rituals

This is NOT spec-as-source (humans edit both specs and code). This is NOT spec-first-then-forget (specs live beyond initial implementation).

---

## The Harness Loop

The full agent pipeline follows a deterministic sequence. The Scrum Master Agent (Sam) orchestrates this loop as a stateless script.

```
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │   Discovery* → Planner → Architect → Design* →              │
  │       ↓                                    ↓                 │
  │   ┌────────────────────────────────────────────────────┐     │
  │   │  Sprint Loop (per story):                          │     │
  │   │    Generator → Gate 1 → Gate 2 → Gate 3 → Gate 4   │     │
  │   │       ↑                          ↓         ↓       │     │
  │   │       └──── rework (if fail) ────┴─────────┘       │     │
  │   └────────────────────────────────────────────────────┘     │
  │                                                              │
  │   * = conditional invocation                                 │
  └──────────────────────────────────────────────────────────────┘
```

### Pipeline Stages

| Stage | Agent | Conditional? | Output |
|-------|-------|-------------|--------|
| Discovery | Discovery Agent (Mary) | Yes — unfamiliar domain, ambiguous scope | product-brief.md |
| Planning | PM Agent (Pat) | No | project-brief.md, prd.md |
| Architecture | Architect Agent (Alex) | No | architecture.md, design.md, readiness verdicts |
| Design | Design Agent (Sally) | Yes — user-facing work only | ux-spec.md |
| Decomposition | Scrum Master Agent (Sam) | No | epics, stories, traceability |
| Generation | Dev Agent (Dana) | No | code, tests, change proposals |
| Evaluation | (Gate system below) | No | pass/rework/fail verdicts |
| Reconciliation | Dev Agent (Dana) | No | updated specs, stories, ops docs |
| Adversarial Review | Red Team Agent (Raze) | Yes — non-trivial changes | adversarial review report (Gate 4) |

### Context Resets Between Agents

**Every agent invocation starts with a fresh context.** No agent inherits conversation history from a previous agent. Each agent receives only the files it needs:

- Discovery Agent: problem statement + domain references
- PM Agent: product-brief.md (if exists) + user requirements
- Architect Agent: prd.md + project-brief.md + existing architecture.md
- Design Agent: prd.md + spec.md + architecture.md
- Dev Agent: story file + spec.md + design.md + ux-spec.md (if exists)
- Adversarial Reviewer (Raze): user request (from ops/metrics.md), git diff, sprint contract, evaluator report, CLAUDE.md

This prevents context pollution and ensures each agent works from the authoritative documents, not from stale conversation state.

---

## Sprint Contract Negotiation

Before a sprint begins, the Scrum Master:

1. **Proposes** a sprint contract — a list of stories selected from the backlog, prioritized by the PM Agent and filtered by the Architect's readiness verdicts
2. **Presents** the contract to the user with effort estimates and dependencies
3. **Negotiates** — the user may add, remove, or reprioritize stories
4. **Locks** the sprint scope once approved

Scope changes after lock require a formal change proposal from the PM Agent. The sprint contract is documented in the epic's story table with a sprint column.

---

## Evaluation Gates

Every story passes through up to four gates before it is marked Done. Gates 1–3 are mandatory; Gate 4 (adversarial review) is mandatory for non-trivial changes (>~50 LOC, security-relevant, new capability, or any change the orchestrator flags as risky).

### Gate 1: Generator Self-Check
- **Who**: Dev Agent (Dana), immediately after implementation
- **What**: The Dev Agent verifies its own work against the story's acceptance criteria
- **Checks**:
  - All acceptance criteria met (checkboxes in story file)
  - All tests pass (unit, integration)
  - Type checks and lint pass
  - REQ-*/SCENARIO-* traceability present in test comments
- **Outcome**: PASS (proceed to Gate 2) or REWORK (fix and re-check)

### Gate 2: Evaluator Verification
- **Who**: A separate agent invocation with evaluator context (not the same context that wrote the code)
- **What**: Independent review of the implementation against the spec
- **Checks**:
  - Code matches design.md contracts
  - Tests actually validate the claimed REQ-*/SCENARIO-* (not just trivially passing)
  - E2E tests pass per ops/e2e-test-plan.md — for scientific Python work this means clean notebook/script execution on sample data, reproducibility verification, and data contract checks
  - No spec-code disagreements introduced
- **Outcome**: PASS (proceed to Gate 3) or CONCERNS (specific issues to address) or FAIL (rework required)

### Gate 3: Final Evaluation
- **Who**: Scrum Master (orchestrator) checks that all artifacts are consistent
- **What**: Reconciliation verification
- **Checks**:
  - spec.md Implementation Status updated
  - Story status updated
  - Epic story table updated
  - Traceability matrix updated
  - ops/status.md and ops/changelog.md updated
  - ops/test-results.md has current E2E results
- **Outcome**: PASS (proceed to Gate 4 if triggered, else DONE) or INCOMPLETE (missing reconciliation artifacts)

### Gate 4: Adversarial Review (Red Team)
- **Who**: Adversarial Reviewer Agent (Raze) — fresh context, read-only, runs LAST
- **What**: Independent post-completion review aimed at finding gaps the other gates missed. Assumes Dana is well-intentioned but rushed; assumes Quinn evaluated the *checklist* rather than the *intent*.
- **Trigger**: Required for non-trivial changes. The orchestrator runs Gate 4 automatically; non-orchestrator Claude sessions spawn Raze as a sub-agent before reporting completion (per CLAUDE.md "Anthropic internal prompt augmentation").
- **Checks** (full rubric in `_bmad/agents/adversarial-reviewer.md`):
  - User request fulfillment — was anything asked for but not delivered? Was scope creep introduced? Were caveats buried?
  - CLAUDE.md compliance — was every mandatory step actually performed (especially Step 5: E2E)?
  - Spec gaps — was every applicable REQ-* addressed? Every SCENARIO-* covered by a real test?
  - Cross-agent blind spots — security/contract/docs-vs-reality drift between Quinn's checklist and ground truth
  - Domain correctness — 3–5 spot-checks of core-product assertions against the spec text they cite (for test-suite products: also false-positive/negative checks against known fixtures)
- **Authority**: Can OVERRIDE a Gate 2 PASS. If Raze and Quinn disagree, Raze wins.
- **Outcome**: APPROVE (DONE) or GAPS_FOUND (rework specific items) or REJECT (return to Generator with full feedback)
- **Output**: `.harness/evaluations/sprint-{N}-adversarial.yaml`

```
Generator → Gate 1 (self) → Gate 2 (evaluator) → Gate 3 (reconciliation) → Gate 4 (adversarial)
    ↑          ↓ fail            ↓ fail                  ↓ incomplete            ↓ gaps/reject
    └─── rework ┘         rework ┘             update docs ┘            rework with Raze report
```

---

## Orchestration Models

### Model A: Scrum Master Script (Default)

The Scrum Master Agent (Sam) is a deterministic script that:
1. Reads state from files on disk
2. Invokes agents in sequence with explicit file-based context
3. Runs evaluation gates
4. Updates status files
5. Repeats until sprint is complete

This model works with any LLM backend. Sam does not reason — Sam follows the pipeline.

### Model B: Claude Code Agent Teams (Alternative)

When using Claude Code with subagent support, the orchestration can leverage agent teams:

- **Orchestrator**: Main Claude Code session acts as Sam, dispatching subagents
- **Subagents**: Each agent role (Discovery, PM, Architect, Design, Dev, Evaluator) runs as a separate subagent with its own context window
- **Context isolation**: Subagents naturally get fresh context per invocation
- **Handoff**: Orchestrator passes file paths (not file contents) to subagents; they read what they need

Benefits of Model B:
- Parallel evaluation (Gate 2 can run as a subagent while the next story's Gate 1 runs)
- Natural context isolation without manual resets
- Token efficiency — each subagent only loads relevant files

The choice between Model A and Model B is an infrastructure decision, not a process decision. The pipeline stages, gates, and artifacts are identical.

---

## Lifecycle Phases (Detailed)

### Phase 1: Discovery (Conditional)
- **Owner**: Discovery Agent (Mary)
- **Trigger**: Unfamiliar domain, ambiguous scope, or user request
- **Outputs**: `_bmad/product-brief.md`
- **Gate**: User confirms product-brief.md captures the problem space accurately

### Phase 2: Planning
- **Owner**: PM Agent (Pat)
- **Outputs**: Project Brief, PRD (FRs, NFRs)
- **Documents**: `_bmad/project-brief.md`, `_bmad/prd.md`

### Phase 3: Architecture
- **Owner**: Architect Agent (Alex)
- **Outputs**: Architecture doc with ADRs, deployment topology, design.md files
- **Documents**: `_bmad/architecture.md`, `openspec/capabilities/*/design.md`
- **Gate**: Implementation readiness check (PASS/CONCERNS/FAIL) per capability

### Phase 4: Design (Conditional)
- **Owner**: Design Agent (Sally)
- **Trigger**: User-facing work (web UI, mobile, interactive CLI)
- **Outputs**: UX specifications
- **Documents**: `openspec/capabilities/*/ux-spec.md`

### Phase 5: Spec Authoring
- **Owner**: Architect + Dev Agents
- **Outputs**: OpenSpec capability specs
- **Documents**: `openspec/capabilities/*/spec.md`

### Phase 6: Epic/Story Decomposition
- **Owner**: Scrum Master Agent (Sam)
- **Outputs**: Epics with story tables, individual story files, traceability matrix
- **Documents**: `epics/epic-*.md`, `epics/stories/s*-*.md`, `_bmad/traceability.md`

### Phase 7: Sprint Execution (per story)
- **Owner**: Dev Agent (Dana), gated by evaluation pipeline
- **Inputs**: Story file + referenced spec.md + design.md + ux-spec.md
- **Process**: TDD (tests first with REQ-*/SCENARIO-* refs) → Implement → Gate 1 → Gate 2 → Gate 3 → Gate 4 (if triggered)
- **Documents**: Source code, test code, `openspec/change-proposals/CP-*.md` (if needed)

### Phase 8: Reconciliation (MANDATORY after each story)
- **Owner**: Dev Agent (Dana)
- **Updates**:
  1. `openspec/capabilities/*/spec.md` — Implementation Status section
  2. `epics/stories/s*-*.md` — Status field, acceptance criteria checkboxes
  3. `epics/epic-*.md` — Story table status
  4. `_bmad/traceability.md` — Impl Status column
  5. `ops/status.md` — What's working, what's next
  6. `ops/changelog.md` — What was done
  7. `ops/test-results.md` — E2E test results

### Course Correction
- If implementation diverges from spec: **update the spec** with rationale, don't silently disagree
- If architecture changes: update `_bmad/architecture.md` and reset "Last Reconciled" date
- If requirements change: PM Agent authors change proposal with delta specs, cascades to affected specs and stories

---

## Document Ownership

| Document | Owner | Update Trigger |
|----------|-------|----------------|
| Product Brief | Discovery Agent | Initial exploration |
| Project Brief | PM | Scope change |
| PRD | PM | Requirements change |
| Architecture | Architect | New component, ADR, or quarterly review |
| Capability Specs | Architect + Dev | New feature, bug fix, or reconciliation |
| UX Specs | Design Agent | New UI capability or UX change |
| Capability Designs | Architect | New capability or design change |
| Epics/Stories | Scrum Master | Sprint planning, story completion |
| Traceability | Scrum Master | Story completion |
| Ops status | Dev | Session end, deploy, or milestone |
| Test results | Dev | After E2E verification |
| Adversarial review report | Adversarial Reviewer (Raze) | After Gate 3, before reporting completion |

## Story Status Lifecycle

```
Backlog → Ready (readiness check passed) → In Progress → Gate 1 → Gate 2 → Gate 3 → Gate 4 → Done
                                               ↓              ↓         ↓         ↓         ↓
                                           Blocked        Rework    Rework    Incomplete  Gaps/Reject
                                       (with blocker)  (with issues)         (missing docs) (Raze report)
```
