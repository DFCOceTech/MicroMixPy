# Operational Status — MicroMixPy

> Last updated: 2026-04-30

## What's Working

- Full processing pipeline: `.mat` → netCDF4
- Data loading: `load_mat` reads all ODAS quicklook variables in physical units
- Downcast extraction: surface soak removal, downcast identification, acceleration flagging
- FP07 calibration: linear regression against JAC-T
- Optical despiking: chlorophyll and turbidity via median-filter MAD
- Oceanographic properties: CT, SA, sigma0 via TEOS-10 (gsw)
- Thorpe scales: density reordering method
- Thermohaline staircase detection: step-detection on fast temperature profile
- Binning: 0.25 dbar uniform grid
- Buoyancy frequency N² via gsw.Nsquared
- Epsilon from sh1 and sh2: iterative Nasmyth spectral fitting (k_min=1, k_max_frac=0.5)
- Chi from FP07 T1/T2: temperature gradient PSD integration
- Best-estimate epsilon: minimum of probe 1 and probe 2
- netCDF4 output: CF-1.8 conventions, all variables with units/long_name
- CLI: `micromixpy process` and `micromixpy info`
- 19/19 unit tests passing

## E2E Test Result (2026-04-30)

Processed DAT_011 profile 1 (SR003):
- eps_best: 54/54 bins valid, range 9e-6 to 1.1e-4 W/kg, median 1.52e-5 W/kg
- chi1: 54/54 bins valid, range 6.5e-10 to 7.5e-6 K²/s
- CT: -0.53 to 3.68 °C, SA: 29.24 to 33.85 g/kg (plausible for LAKO fjord)
- Thorpe scale max: 1.6 m
- Metadata correctly assigned: station SR003, lat 69.3379, lon -25.14338

## Known Issues / Limitations

- No Goodman vibration correction applied to shear probes (Ax/Ay available but not used).
  This may cause epsilon overestimation in turbulent regions where vehicle vibration is significant.
- Metadata CSV only covers through DAT_070; later files require `--skip-missing-meta`.
- Thorpe scales computed at slow (JAC) rate; may miss fine-scale structure.
- N² can be negative (raw density inversions) — consider smoothing before computing N².

## What's Next

1. Add Goodman vibration correction to shear spectra (`src/micromixpy/turbulence/goodman.py`)
2. Process full dataset (65 .mat files, ~250 profiles)
3. Add batch processing progress bar
4. Consider parallel processing for the full dataset
5. Add diagnostic plots (epsilon profile, shear spectra per bin)
6. Validate epsilon values against the chi-based epsilon proxy: eps ~ 0.2 * N² * chi / (dT/dz)²
7. Write results to a consolidated netCDF or CSV summary for analysis

## Conda Environment

- Name: `vmpmix`
- Python: 3.11.15
- Location: `~/miniconda3/envs/vmpmix/`
