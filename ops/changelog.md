# Changelog — MicroMixPy

Rolling 2-week work log. Remove entries older than 2 weeks.

## 2026-05-03
- **Deceleration flag** (`processing/downcasts.py`): Added `_deceleration_flag()` to flag
  samples at the end of the downcast where smoothed fall speed drops below 90 % of terminal
  velocity. Combined with existing `_acceleration_flag()` into `accel_flag` so tether-tension-
  contaminated bins are automatically excluded from epsilon and chi. Eliminates artefactual
  epsilon spike at deepest profile bins.
- **Thorpe scale non-monotonic depth** (`oceanography/thorpe.py`): `compute_thorpe_scales`
  now sorts valid-sample arrays by depth (stable sort) before calling mixsea, then inverse-sorts
  results back to original indices. Fixes silent all-zero Thorpe output for profiles with minor
  pressure reversals (e.g. SR005 from DAT_011.mat).
- **Spec**: REQ-TDISS-007, REQ-TDISS-008 and three SCENARIO-* entries added to
  `openspec/capabilities/turbulence-dissipation/spec.md`. Structural corruption (duplicate
  `## Scenarios` headers, misplaced REQ-TDISS-005/006) corrected.
- **Tests**: SCENARIO-TDISS-007-A, -007-B, and -008-A covered in `test_processing.py` and
  `test_oceanography.py`. 57 tests passing.
