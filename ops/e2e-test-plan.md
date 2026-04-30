# E2E Test Plan — {{PROJECT_NAME}}

> Last updated: {{DATE}}

## E2E Testing Policy (MANDATORY)

Every change derived from user instruction MUST be verified end-to-end before reporting done. For scientific Python / notebook work, "end-to-end" means the full execution of the artifact (script or notebook) from inputs to outputs in the project's conda environment — not mocked dependencies, not partial cell execution.

## E2E Categories by Artifact Type

### Category 1: Python Scripts / CLI Tools
- **Method**: Subprocess invocation of the actual entry point
- **Command**: `python scripts/<name>.py --args ...` (or equivalent)
- **Pass criteria**: Exit code 0, output artifacts present, spot-check values against known expectations
- **When**: Every change to script logic or its dependencies

### Category 2: Jupyter Notebooks
- **Method**: `jupyter nbconvert --to notebook --execute <notebook>.ipynb --output <output>.ipynb`
- **Pass criteria**: Execution completes without error, output cells populated, key output values match expected range/type
- **Alternative**: `pytest --nbmake notebooks/` (if nbmake is installed)
- **When**: Every change to notebook cells or data inputs

### Category 3: Data Pipelines (multi-step)
- **Prerequisites**: Representative sample dataset in `tests/fixtures/` or `data/test/`
- **Method**: Run the full pipeline on sample data; compare output schema, CRS (for GIS), row counts, and key statistics to known-good reference outputs
- **When**: Any change that affects data transformation logic or output schema

### Category 4: Visualization / Figure Generation
- **Method**: Execute figure-generation code; verify output file is produced and is non-empty
- **Optional deep check**: Visual regression via image hash comparison against a stored reference figure
- **When**: Changes to plotting code

## Reproducibility Requirement

All analyses MUST be reproducible. If randomness is involved:
- Fix the random seed explicitly (`numpy.random.seed(N)`, `random.seed(N)`)
- Document the seed in the spec
- Reproducibility check: run twice with same inputs; outputs must be bit-identical (or within documented numerical tolerance for floating-point)

## Test Scenarios

| ID | Scenario | Category | Status |
|----|----------|----------|--------|
| E2E-001 | {{scenario}} | {{1/2/3/4}} | {{Pass/Fail/Not Run}} |

## How to Run

```bash
# Activate environment first
conda activate <env_name>

# Unit tests (scripts, helper modules)
pytest tests/ -v --tb=short

# Notebook execution tests (requires nbmake: pip install nbmake)
pytest --nbmake notebooks/ -v

# Single notebook manual E2E
jupyter nbconvert --to notebook --execute notebooks/<name>.ipynb \
  --output /tmp/<name>_executed.ipynb

# Full pipeline E2E on sample data
python scripts/run_pipeline.py --data tests/fixtures/sample/ --output /tmp/e2e_out/

# Lint + type checks
ruff check .
mypy src/
```

## Data Fixture Strategy

- Place representative small datasets in `tests/fixtures/` — never raw/full data
- Reference outputs (known-good) go in `tests/fixtures/expected/`
- For GIS: include a small clipped shapefile or GeoJSON covering the test area
- Fixtures must be synthetic or publicly licensed — never include PII or restricted data
