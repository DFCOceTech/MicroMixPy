# CLAUDE.md — MicroMixPy

Claude Code follows these instructions when coding in this repository.

## Anthropic internal prompt augmentation

If the user's request is based on a misconception, say so.
Never claim 'all tests pass' when output shows failures.
Keep text between tool calls to <=25 words.
Spawn an adversarial sub-agent (the Red Team / Raze, defined in `_bmad/agents/adversarial-reviewer.md`) to review non-trivial changes before reporting completion.

## Git, Secrets & Environment (MANDATORY)

Before any `git add`, `git commit`, `git push`, branch operation, or `pip install` / `conda install`, read and follow **`ops/git-workflow.md`**. No exceptions.

Key invariants (always in effect):
- Never commit secrets, credentials, or `.env` files
- Never install packages outside the `vmpmix` conda environment
- Never commit directly to `main` without explicit user approval
- Data files (`.mat`, `.nc`) are listed in `.gitignore` and must never be committed

## Project Overview

**MicroMixPy** is an ODAS-like turbulent mixing processing pipeline for VMP-250
microstructure profiler data from the LAKO 2018 cruise (proglacial fjord, NE Greenland).

### Key science decisions
- `sh1`/`sh2` in the ODAS .mat files are **already in s⁻¹** (ODAS quicklook applied full calibration including speed division). Do NOT apply a second calibration.
- FP07 temperatures (`T1_fast`, `T2_fast`) are in °C but must be calibrated against JAC-T via linear regression before turbulence processing.
- Chlorophyll and Turbidity are at **fast rate (512 Hz)**, not slow rate.
- Epsilon is estimated via iterative Nasmyth spectral fitting with `k_max_frac=0.5` and `k_min=1 cpm`.
- Chi is estimated by integrating the temperature gradient PSD (from calibrated T1/T2 numerical dT/dz).

### Data paths (read-only)
- `.mat` files: `/Users/carlson/Documents/Pubs_in_progress/LAKO_Mixing/data_analysis/mat_files/`
- Metadata CSV: `/Users/carlson/Documents/Pubs_in_progress/LAKO_Mixing/data_analysis/vmp_positions_corrected.csv`
- Existing scripts reference: `/Users/carlson/Documents/Pubs_in_progress/LAKO_Mixing/data_analysis/scripts/`

**All files under `/Users/carlson/Documents/Pubs_in_progress/LAKO_Mixing/` are read-only.**

## Development Workflow (MANDATORY)

Use **spec-anchored development** (BMAD + OpenSpec). Every code change follows:

1. **Spec First** — Update `openspec/capabilities/*/spec.md` with new REQ-* and SCENARIO-*.
2. **Write Tests** — Tests reference REQ-* and SCENARIO-* in comments.
3. **Implement** — Code to satisfy spec requirements.
4. **Verify** — `pytest tests/ -v --tb=short` (all tests must pass)
5. **E2E Verify (MANDATORY)** — Process at least one real profile. Verify eps/chi are physically plausible (eps ~ 1e-10 to 1e-4 W/kg for fjord waters).
6. **Sanitize & Commit** — Follow `ops/git-workflow.md`.
7. **Reconcile Specs** — Update spec implementation status.
8. **Update Ops** — Update `ops/status.md` and `ops/changelog.md`.

## Build / Test / Deploy

```bash
# Activate environment (ALWAYS use this env)
conda activate vmpmix

# Install in editable mode
pip install -e ".[dev]"

# Unit tests
pytest tests/ -v --tb=short

# Lint & type-check
ruff check src/
mypy src/micromixpy/

# Format
ruff format src/

# E2E test — process all profiles from DAT_011.mat
micromixpy process \
  /Users/carlson/Documents/Pubs_in_progress/LAKO_Mixing/data_analysis/mat_files/DAT_011.mat \
  --metadata /Users/carlson/Documents/Pubs_in_progress/LAKO_Mixing/data_analysis/vmp_positions_corrected.csv \
  --output-dir /tmp/micromixpy_out

# CLI info command
micromixpy info <file.mat>
```

## Session Metrics (MANDATORY)

Track execution time and token consumption every turn.
Log in `ops/metrics.md`.

## Key Paths

| What | Where |
|------|-------|
| Package source | `src/micromixpy/` |
| IO modules | `src/micromixpy/io/` |
| Processing modules | `src/micromixpy/processing/` |
| Oceanography modules | `src/micromixpy/oceanography/` |
| Turbulence modules | `src/micromixpy/turbulence/` |
| CLI | `src/micromixpy/cli/main.py` |
| Pipeline | `src/micromixpy/pipeline.py` |
| Unit tests | `tests/` |
| BMAD strategic docs | `_bmad/` |
| Capability specs | `openspec/capabilities/*/spec.md` |
| Operational status | `ops/status.md` |
| Data sources | `ops/data-sources.md` |
| Work log | `ops/changelog.md` |
| E2E test plan | `ops/e2e-test-plan.md` |
| Session metrics | `ops/metrics.md` |
| Git workflow | `ops/git-workflow.md` |
| Old Python reference | `old_python/` |
| Environment spec | `environment.yml` |
| Requirements | `requirements.txt` |
