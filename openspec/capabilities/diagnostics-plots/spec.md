# Capability: Diagnostic Plots

**Capability ID**: diagnostics-plots  
**Status**: In Development  
**Last Updated**: 2026-05-01

---

## Requirements

### REQ-PLOT-001 — Output location and naming
All plots SHALL be saved as PNG files in a subdirectory named
`{file_stem}_P{profile_num:02d}_{station}/` inside the `--output-dir`.
Each figure SHALL be named after its content, e.g. `ts_diagram.png`,
`epsilon_profiles.png`.

### REQ-PLOT-002 — T-S diagram (simple)
A T-S diagram (SA on x-axis, CT on y-axis) SHALL be produced from the binned
CTD profile.

### REQ-PLOT-003 — T-S diagram with Gade line
The T-S diagram SHALL optionally overlay the Gade (1979) glacial meltwater
mixing line.  The line is defined by:
  T(S) = T_FW + (T_AW - T_FW) · S / S_AW
where T_FW = T_ice - L_ice / c_pw (latent heat correction; default T_ice = -2°C,
L_ice = 334000 J/kg, c_pw = 3985 J/(kg·K)) and (T_AW, S_AW) default to the
warmest/saltiest point in the profile.  All four parameters SHALL be
user-tunable.

### REQ-PLOT-004 — T-S diagram coloured by scalar
The T-S scatter plot SHALL support colouring each point by any binned scalar
variable (e.g. turbidity, chi_best, regime code).

### REQ-PLOT-005 — Epsilon profile (log-scale)
A vertical profile figure SHALL show eps1, eps2, and eps_best on a log10
x-axis with depth on the y-axis (increasing downward).

### REQ-PLOT-006 — Chi profile
A vertical profile figure SHALL show chi1, chi2, and chi_best on a log10
x-axis with depth on the y-axis.

### REQ-PLOT-007 — Chi-epsilon regime diagram
A scatter plot of log10(chi_best) vs. log10(eps_best) SHALL colour points by
mixing regime (REQ-REGIME-001) and shade the three regime regions.

### REQ-PLOT-008 — Annotated temperature profile
A vertical temperature profile (from fast FP07) SHALL annotate depth ranges
where: (a) staircase_flag=1, (b) regime=double_diffusion (Tu≈70°), and
(c) regime=turbulent_mixing.

### REQ-PLOT-009 — CLI integration
A `micromixpy plot <netcdf_file>` subcommand SHALL generate all figures for a
processed netCDF file, writing them to the same directory as the netCDF.

---

## Implementation Status

| Requirement | Status | Notes |
|-------------|--------|-------|
| REQ-PLOT-001 | ✅ Implemented | `diagnostics/plots.py` |
| REQ-PLOT-002 | ✅ Implemented | `plot_ts` |
| REQ-PLOT-003 | ✅ Implemented | `plot_ts_gade` |
| REQ-PLOT-004 | ✅ Implemented | `plot_ts_scalar` |
| REQ-PLOT-005 | ✅ Implemented | `plot_epsilon_profiles` |
| REQ-PLOT-006 | ✅ Implemented | `plot_chi_profiles` |
| REQ-PLOT-007 | ✅ Implemented | `plot_chi_epsilon_diagram` |
| REQ-PLOT-008 | ✅ Implemented | `plot_temperature_profile` |
| REQ-PLOT-009 | ✅ Implemented | `micromixpy plot` CLI subcommand |
