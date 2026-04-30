# {{Capability Name}} — Design

> Version: 1.0 | Status: Draft | Last updated: {{DATE}}

## Implementation Approach

{{Describe the implementation strategy: is this a notebook, a script, a reusable module, or a combination? What is the execution entry point?}}

## Pipeline / Analysis Flow

```
{{Step-by-step data flow, e.g.:
  data/raw/X.csv
    → load & validate (src/ingest.py)
    → clean & transform (notebooks/01_clean.ipynb)
    → spatial join (src/geo_utils.py)
    → aggregate (notebooks/02_analysis.ipynb)
    → figures (figures/map_output.png)
    → data/processed/output.csv
}}
```

## Key Functions / Modules

| Module / Notebook | Responsibility | Key Functions |
|-------------------|----------------|---------------|
| `{{src/module.py}}` | {{What it does}} | `{{function_name()}}` |
| `{{notebooks/NN_name.ipynb}}` | {{What it analyzes}} | — |

## Data Contracts

### Architect Constraints (MUST / MUST NOT / SHOULD)

- **MUST**: {{e.g., reproject all inputs to EPSG:XXXX before spatial operations}}
- **MUST NOT**: {{e.g., modify any file under data/raw/}}
- **SHOULD**: {{e.g., use vectorized pandas operations rather than row-by-row loops}}

### Configuration

```yaml
# {{config file or environment variables this capability reads}}
{{config_key}}: {{default_value}}  # {{description}}
```

## Error Handling

| Error Condition | Response | Recovery |
|-----------------|----------|----------|
| Input file missing | Raise `FileNotFoundError` with path | Check `ops/data-sources.md` for download instructions |
| CRS mismatch | Raise `ValueError` with actual vs. expected CRS | Reproject source data before running |
| Unexpected nulls | Log warning, document count, proceed or raise per spec | {{as appropriate}} |

## Dependencies

- {{List key library dependencies and version constraints, e.g., geopandas>=0.14, rasterio>=1.3}}
