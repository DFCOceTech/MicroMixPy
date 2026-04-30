# Session Metrics — {{PROJECT_NAME}}

## How Metrics Are Collected

- **Wall-clock time**: `date -u` at start/end of each turn
- **Main conversation tokens**: Extracted from session JSONL via `python3 scripts/session-metrics.py`
  - Source: `~/.claude/projects/{{PROJECT_SLUG}}/{session-id}.jsonl`
  - Every assistant message contains a `usage` object with: `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`
- **Subagent tokens**: From agent result metadata (`total_tokens`, `duration_ms`)
- **Cost**: Computed using current model pricing (see `scripts/session-metrics.py`)

## Turn Log

| Turn | Start (UTC) | End (UTC) | Duration | Description |
|------|-------------|-----------|----------|-------------|
| 1 | | | | |

## Subagent Token Usage

| Agent | Tokens | Duration | Task |
|-------|--------|----------|------|
| | | | |

## Session Summary

Run `python3 scripts/session-metrics.py` to fill this section.

| Category | Tokens | Cost |
|----------|--------|------|
| Input | | |
| Output | | |
| Cache Write | | |
| Cache Read | | |
| **TOTAL** | | |
