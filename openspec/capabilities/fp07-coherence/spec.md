# Capability: Dual-Thermistor Noise Rejection

**Capability ID**: fp07-coherence  
**Status**: In Development  
**Last Updated**: 2026-05-01

---

## Problem Statement

The VMP-250 carries two FP07 thermistors (T1, T2).  In the absence of real turbulence the
two probes should measure identical temperature gradients; divergence indicates noise
contamination in one or both sensors.  Reporting chi from a noisy bin inflates the
dissipation estimate.

---

## Requirements

### REQ-FP07-001 — Spectral coherence quality flag
For each depth bin, the Batchelor fitting SHALL compute the spectral coherence between
the T1 and T2 temperature gradient spectra in the Batchelor fitting band.
Bins where the mean squared coherence falls below a user-specifiable threshold
(default 0.5) SHALL be flagged as low-quality.

### REQ-FP07-002 — Flagged-bin handling
Flagged bins SHALL have chi and eps_batchelor set to NaN in the default pipeline.
The raw (un-masked) chi values and the coherence value SHALL be retained as
separate netCDF variables for diagnostic use.

### REQ-FP07-003 — Best-estimate chi
A `chi_best` variable SHALL be computed as the mean of chi1 and chi2 for bins
that pass the coherence flag in both probes; falling back to the passing probe
when only one passes; NaN when both fail.

---

## Scenarios

### SCENARIO-FP07-001 — High coherence preserves chi
Given two identical temperature gradient signals (coherence ≈ 1),
When the coherence check is applied with threshold=0.5,
Then the bin is NOT flagged and chi is retained.

### SCENARIO-FP07-002 — Low coherence flags bin
Given two uncorrelated temperature gradient signals (coherence ≈ 0),
When the coherence check is applied with threshold=0.5,
Then the bin IS flagged and chi is NaN.

---

## Implementation Status

| Requirement | Status | Notes |
|-------------|--------|-------|
| REQ-FP07-001 | ✅ Implemented | `fp07_coherence.compute_inter_thermistor_coherence` |
| REQ-FP07-002 | ✅ Implemented | chi1/chi2 masked; chi1_raw/chi2_raw retained |
| REQ-FP07-003 | ✅ Implemented | `chi_best` in pipeline and netCDF |
