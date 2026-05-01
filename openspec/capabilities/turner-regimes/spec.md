# Capability: Turner Angle and Mixing Regime Classification

**Capability ID**: turner-regimes  
**Status**: In Development  
**Last Updated**: 2026-05-01

---

## Requirements

### REQ-TURNER-001 — Turner angle from binned CTD data (default)
The Turner angle and density ratio R_rho SHALL be computed from the binned CTD
(JAC-T, JAC-C) profile using gsw.Turner_Rsubrho, on the same 0.25 dbar grid.
A `turner_source` parameter SHALL allow the user to specify 'binned' (default)
or 'fast' (FP07 fast-rate data).

### REQ-REGIME-001 — Mixing regime classification (Bouffard & Boegman 2013)
Each epsilon/chi depth bin SHALL be classified into one of four regimes using the
buoyancy Reynolds number Reb = ε / (ν · N²) and Turner angle Tu:

| Regime | Condition |
|--------|-----------|
| `turbulent_mixing`  | Reb ≥ 20 and \|Tu\| < 45° |
| `double_diffusion`  | Reb < 20 and \|Tu\| ≥ 45° |
| `weak_mixing`       | Reb < 20 and \|Tu\| < 45° |
| `indeterminate`     | N² ≤ 0 or missing data |

Reference: Bouffard & Boegman (2013), J. Geophys. Res. Oceans, 118, 5871-5887.

### REQ-REGIME-002 — Regime stored in netCDF as integer code
Regimes SHALL be encoded as integers: 0=indeterminate, 1=turbulent_mixing,
2=double_diffusion, 3=weak_mixing, with a flag_meanings attribute.

---

## Scenarios

### SCENARIO-TURNER-001 — Turner angle sign convention
Positive Turner angle (Tu > 0) SHALL indicate salt-fingering-favourable conditions;
negative (Tu < 0) diffusive-layering-favourable; |Tu| = 90° maximally unstable.

### SCENARIO-REGIME-001 — Classification logic
Given Reb = 50 and Tu = 20°, regime SHALL be turbulent_mixing.
Given Reb = 5 and Tu = 70°, regime SHALL be double_diffusion.
Given Reb = 5 and Tu = 20°, regime SHALL be weak_mixing.

---

## Implementation Status

| Requirement | Status | Notes |
|-------------|--------|-------|
| REQ-TURNER-001 | ✅ Implemented | `oceanography/turner.py` |
| REQ-REGIME-001 | ✅ Implemented | `turbulence/regimes.py` |
| REQ-REGIME-002 | ✅ Implemented | integer codes in netCDF |
