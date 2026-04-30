# Data Sources & External Resources — MicroMixPy

> Last updated: 2026-04-30

## Local Data Paths (ALL READ-ONLY)

| Dataset | Local Path | Format | Notes |
|---------|-----------|--------|-------|
| VMP-250 .mat files | `/Users/carlson/Documents/Pubs_in_progress/LAKO_Mixing/data_analysis/mat_files/` | MATLAB .mat (ODAS quicklook) | 65 files, DAT_011 to DAT_070+ |
| Deployment metadata | `/Users/carlson/Documents/Pubs_in_progress/LAKO_Mixing/data_analysis/vmp_positions_corrected.csv` | CSV | Station_Name, Date, Time, Lat, Lon, File_Name, Profile. Complete through DAT_070. |
| Old Python scripts | `/Users/carlson/Documents/Pubs_in_progress/LAKO_Mixing/data_analysis/scripts/` | .py, .ipynb | Reference only — not production code |
| Old Python scripts (repo copy) | `old_python/` | .py, .ipynb | Same files, local reference copy |

## Instrument Details

**Rockland Scientific VMP-250 (SN 295)**
- Fast sensors (512 Hz): pressure (P), FP07 thermistors (T1, T2), shear probes (sh1, sh2), JAC backscatter (Chlorophyll, Turbidity), accelerometers (Ax, Ay)
- Slow sensors (64 Hz): JAC CT (JAC_T, JAC_C)
- ODAS quicklook outputs all signals in physical units; sh1/sh2 are in s⁻¹

**Shear probe calibration (from setupfilestr):**
- sh1: sens=0.1022 V·s/m, diff_gain=0.932, SN M1854, cal 2018-04-17
- sh2: sens=0.1085 V·s/m, diff_gain=0.942, SN M1860, cal 2018-04-17

## Conda Environment

- **Name**: `vmpmix`
- **Python**: 3.11
- **Key packages**: scipy, gsw, numpy, xarray, netCDF4, matplotlib, pandas

## Output

Output netCDF files are written to a user-specified directory at runtime via `--output-dir`.
They are NOT committed to git (covered by `.gitignore`).
