# Project Conventions

**Last Updated**: {{ISO date}}
**Status**: Template — fill in for your project

This file defines project-wide conventions that all agents and contributors must follow. It is the authoritative source for naming, file organization, coding standards, and tooling decisions.

## Project Identity

- **Name**: {{Project name}}
- **Language**: Python {{version, e.g., 3.11}}
- **Primary libraries**: {{e.g., pandas, geopandas, numpy, scipy, matplotlib, seaborn, plotly, rasterio, shapely, pyproj}}
- **Package manager**: conda (Miniforge/Mambaforge preferred)
- **Conda environment**: {{env_name}} — see `environment.yml`

## File Organization

```
{{project-root}}/
  _bmad/                  # Strategic documents (PRD, architecture)
  openspec/               # Specifications
    capabilities/         # Capability specs and designs
    change-proposals/     # Spec change proposals
  epics/                  # Epics and stories
    stories/              # Individual story files
  ops/                    # Operational documents (status, changelog, known issues)
  .harness/               # Agentic harness
    config.yaml           # Harness configuration
    prompts/              # Agent role prompts
    contracts/            # Sprint contracts
    handoffs/             # Agent handoff files
    evaluations/          # Evaluation reports
  notebooks/              # Jupyter notebooks (numbered, ordered)
  src/                    # Reusable Python modules and packages
    {{package_name}}/
  tests/                  # Unit and integration tests
    fixtures/             # Small representative datasets and expected outputs
      expected/           # Known-good reference outputs for E2E comparison
  data/                   # Data files (gitignored except fixtures)
    raw/                  # Immutable original inputs — never modified
    external/             # Third-party reference data
    interim/              # Intermediate transformed data
    processed/            # Analysis-ready outputs
  figures/                # Generated figures and maps (gitignored or selectively committed)
  scripts/                # One-off utility scripts, pipeline entry points
  environment.yml         # Conda environment specification
  requirements.txt        # pip freeze export
```

## Naming Conventions

### Notebooks
- Prefix with a two-digit sequence number: `01_data-ingest.ipynb`, `02_exploratory-analysis.ipynb`
- Use kebab-case after the prefix
- Name reflects the analysis goal, not the date

### Python Files and Directories
- Files and directories: `snake_case`
- Test files: `test_{module_name}.py`

### Code

#### Variables and Functions
- `snake_case`
- Boolean variables: `is_`, `has_`, `should_` prefixes
- Functions that return data: descriptive noun phrases (`get_study_area()`, `load_elevation_raster()`)

#### Classes
- `PascalCase`

#### Constants
- `UPPER_SNAKE_CASE`

### Spec Identifiers
- Requirements: `REQ-{CAP}-{NNN}` (e.g., REQ-INGEST-001, REQ-VIZ-003)
- Scenarios: `SCENARIO-{CAP}-{FLOW}-{NNN}` (e.g., SCENARIO-INGEST-LOAD-001)
- Change Proposals: `CP-{NNN}`
- ADRs: `ADR-{NNN}`
- Stories: `STORY-{EPIC}-{NNN}`
- Epics: `EPIC-{NNN}`

## Coding Standards

### General
- Max line length: 100 characters (configured in `ruff.toml` or `pyproject.toml`)
- Indentation: 4 spaces
- Trailing newline: required
- Import order: standard library → third-party → local (enforced by ruff/isort)

### Reproducibility (MANDATORY)
- Any analysis involving randomness MUST fix the random seed explicitly
- Document the seed value in the relevant spec SCENARIO
- Do not read system time or use `uuid4()` in analytical code paths
- Pin dependency versions in `environment.yml` and `requirements.txt`

### Docstrings
- Format: **NumPy style** for all public functions and classes
- One-line docstring acceptable for private helpers
- Notebooks: use Markdown cells to document intent and methodology; code cells stay uncommented except for non-obvious steps

### Data / CRS Handling
- Always document units (meters, degrees, etc.) in variable names or docstrings
- Reproject to the project CRS (see `ops/data-sources.md`) before any spatial join or analysis
- Never mutate a `raw/` input file
- Prefer `pathlib.Path` over string paths

### Error Handling
- Validate data inputs at pipeline boundaries (shape, dtype, CRS, null count)
- Use `assert` for internal invariants; raise `ValueError` with a message for user-facing errors
- Log warnings via the standard `logging` module — never `print()` in library code

## Build and Run Commands

```bash
# Activate environment
conda activate <env_name>

# Install / update deps
pip install -e ".[dev]"
# or:
pip install -r requirements.txt

# Unit tests
pytest tests/ -v --tb=short

# Notebook E2E (requires nbmake)
pytest --nbmake notebooks/ -v

# Lint
ruff check .

# Format
ruff format .

# Type check
mypy src/

# Coverage
pytest tests/ --cov=src --cov-report=term-missing

# Execute a single notebook to verify
jupyter nbconvert --to notebook --execute notebooks/<name>.ipynb \
  --output /tmp/<name>_executed.ipynb
```

## Dependencies Policy

- All packages installed inside the named conda environment — never base or system Python
- Add new packages to `environment.yml` and export `requirements.txt` after install
- Prefer conda-forge channel for geospatial packages (GDAL, PROJ, rasterio, geopandas)
- Security scan: `pip-audit` or `safety check`

## Git Conventions

### Branch Naming
- `feature/{story-id}-{short-description}`
- `fix/{story-id}-{short-description}`
- `analysis/{short-description}` (for exploratory branches not tied to a story)

### Commit Messages
- Conventional Commits: `feat:`, `fix:`, `data:`, `analysis:`, `docs:`, `test:`, `refactor:`, `chore:`
- Reference the story ID in the body when applicable

### Pull Requests
- PR description must state: what changed, what data was used, how results were verified
- CI must pass (lint, unit tests, notebook execution on sample data)

## Environment and Configuration

- Secrets (API keys, data service credentials) loaded from `.env` — never committed
- `.env.example` contains placeholder values; document every variable
- Configuration that varies by environment goes in a YAML config file, not hardcoded

## Data Gitignore Rules

Large data files are gitignored. Only commit:
- `data/` — nothing (all data is local or downloaded via scripts)
- `tests/fixtures/` — small synthetic or publicly licensed sample data only
- `figures/` — selectively commit publication-ready figures; ignore intermediate ones

See `.gitignore` for the full ruleset.
