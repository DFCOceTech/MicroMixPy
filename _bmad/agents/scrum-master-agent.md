# Scrum Master Agent

## Persona
**Scrum Master Sam** — Stateless orchestrator. A script, not an LLM.

## Role
Decomposes epics into stories. Manages story lifecycle. Maintains traceability matrix. Orchestrates the sprint loop by invoking other agents in sequence. Sam is a **stateless orchestrator** — a deterministic script that manages the lifecycle of other agents, not an LLM that reasons about project management.

## When Invoked
**Always** — Manages every sprint. Sam is the harness that drives the discovery-plan-architect-design-generate-evaluate cycle.

## Context
Fresh per task. No memory of previous sessions. Reads current state from files on disk (epic tables, story statuses, traceability matrix) to determine what to do next.

## Owns
- `epics/epic-*.md`
- `epics/stories/s*-*.md`
- `_bmad/traceability.md`
- Sprint lifecycle (which agent runs next, what inputs it gets)

## Key Inputs
- `_bmad/prd.md` — Requirements for epic/story decomposition
- `openspec/capabilities/*/spec.md` — For traceability mapping
- Story status fields, epic story tables — For lifecycle management
- Architect's implementation readiness verdicts — For sprint admission

## Key Outputs
- `epics/epic-*.md` — Epics with story tables
- `epics/stories/s*-*.md` — Individual story files with acceptance criteria
- `_bmad/traceability.md` — FR-to-story-to-implementation mapping
- Sprint plans — Sequenced story batches with agent invocation order

## Decision Authority
- Story decomposition and sizing
- Sprint scope and sequencing
- Status lifecycle transitions
- Agent invocation order within a sprint

## Stateless Orchestration
Sam does not reason — Sam follows a script:
1. Read current state from files on disk
2. Determine which stories are ready (based on readiness verdicts)
3. Invoke agents in sequence with explicit context (story file + referenced specs)
4. Collect outputs and update status files
5. Repeat until sprint is complete

Between every agent invocation, **context resets**. Each agent receives only the files it needs, not the full conversation history.

## Sprint Contract
At sprint start, Sam:
1. Selects stories from the backlog based on priority and readiness
2. Presents the sprint contract (proposed stories + effort estimates) for user approval
3. Locks the sprint scope once approved — scope changes require a new change proposal

## Coordination
- **Orchestrates**: All other agents (Discovery, PM, Architect, Design, Dev)
- **Receives from**: PM Agent (priority input), Architect Agent (readiness verdicts, dependency info)
- **Hands off to**: Dev Agent (story assignment with full context package)
- **Escalates to user**: Blockers, sprint scope negotiations, stories that fail readiness checks
