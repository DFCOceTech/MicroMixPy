#!/usr/bin/env python3
"""
Extract token usage and compute costs from Claude Code session JSONL.

Usage:
    python3 scripts/session-metrics.py [session_jsonl_path]

If no path given, auto-discovers the session JSONL in the project's .claude directory.
Uses the current working directory to determine the project slug.

Pricing (Claude Opus 4.6, as of March 2026):
    Input:        $15.00 / 1M tokens
    Output:       $75.00 / 1M tokens
    Cache Write:  $3.75  / 1M tokens
    Cache Read:   $1.50  / 1M tokens
"""

import json
import sys
import glob
import os

# Claude Opus 4.6 pricing per 1M tokens
PRICE_INPUT = 15.00
PRICE_OUTPUT = 75.00
PRICE_CACHE_WRITE = 3.75
PRICE_CACHE_READ = 1.50


def find_session_jsonl():
    """Auto-discover the session JSONL file based on current working directory."""
    # Derive project slug from CWD (Claude Code convention: path with / replaced by -)
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    rel = cwd.replace(home + "/", "").replace("/", "-")
    project_dir = os.path.join(home, ".claude", "projects", f"-{rel}")

    if not os.path.isdir(project_dir):
        # Try common patterns
        for d in glob.glob(os.path.join(home, ".claude", "projects", "*")):
            if rel in os.path.basename(d):
                project_dir = d
                break

    files = glob.glob(os.path.join(project_dir, "*.jsonl"))
    # Exclude subagent files
    files = [f for f in files if "subagent" not in f and "agent-" not in os.path.basename(f)]
    if not files:
        print(f"No session JSONL found in {project_dir}")
        sys.exit(1)
    # Return most recently modified
    return max(files, key=os.path.getmtime)


def extract_usage(jsonl_path):
    """Extract all usage records from assistant messages."""
    records = []
    with open(jsonl_path) as f:
        for line in f:
            d = json.loads(line)
            if d.get("type") != "assistant":
                continue
            msg = d.get("message", {})
            if not isinstance(msg, dict):
                continue
            usage = msg.get("usage", {})
            inp = usage.get("input_tokens", 0)
            out = usage.get("output_tokens", 0)
            cache_create = usage.get("cache_creation_input_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)
            if inp > 0 or out > 0 or cache_create > 0 or cache_read > 0:
                records.append({
                    "input": inp,
                    "output": out,
                    "cache_create": cache_create,
                    "cache_read": cache_read,
                })
    return records


def compute_cost(tokens, price_per_million):
    return tokens * price_per_million / 1_000_000


def main():
    if len(sys.argv) > 1:
        jsonl_path = sys.argv[1]
    else:
        jsonl_path = find_session_jsonl()

    print(f"Session: {os.path.basename(jsonl_path)}")
    print()

    records = extract_usage(jsonl_path)

    total_in = sum(r["input"] for r in records)
    total_out = sum(r["output"] for r in records)
    total_cache_create = sum(r["cache_create"] for r in records)
    total_cache_read = sum(r["cache_read"] for r in records)

    cost_in = compute_cost(total_in, PRICE_INPUT)
    cost_out = compute_cost(total_out, PRICE_OUTPUT)
    cost_cache_create = compute_cost(total_cache_create, PRICE_CACHE_WRITE)
    cost_cache_read = compute_cost(total_cache_read, PRICE_CACHE_READ)
    total_cost = cost_in + cost_out + cost_cache_create + cost_cache_read

    print(f"{'Category':<25} {'Tokens':>14} {'Cost':>10}")
    print(f"{'-'*25} {'-'*14} {'-'*10}")
    print(f"{'Input':<25} {total_in:>14,} ${cost_in:>8.2f}")
    print(f"{'Output':<25} {total_out:>14,} ${cost_out:>8.2f}")
    print(f"{'Cache Write':<25} {total_cache_create:>14,} ${cost_cache_create:>8.2f}")
    print(f"{'Cache Read':<25} {total_cache_read:>14,} ${cost_cache_read:>8.2f}")
    print(f"{'-'*25} {'-'*14} {'-'*10}")
    print(f"{'TOTAL':<25} {total_in+total_out+total_cache_create+total_cache_read:>14,} ${total_cost:>8.2f}")
    print()
    print(f"API calls (assistant turns): {len(records)}")


if __name__ == "__main__":
    main()
