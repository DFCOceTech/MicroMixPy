"""Tests for dual-thermistor noise rejection via spectral coherence.

REQ-FP07-001: spectral coherence between T1 and T2 gradient spectra flags noisy bins.
REQ-FP07-002: flagged bins have chi=NaN; raw chi and coherence retained.
REQ-FP07-003: chi_best uses passing probes.
"""

import numpy as np
import pytest

from micromixpy.turbulence.fp07_coherence import inter_thermistor_coherence


_FS = 512.0
_W = 0.6
_N = 4096


class TestInterThermistorCoherence:
    def test_identical_signals_high_coherence(self):
        """SCENARIO-FP07-001: identical T signals → coherence near 1."""
        rng = np.random.default_rng(0)
        T = rng.normal(0, 0.05, _N).cumsum() * 0.001
        coh = inter_thermistor_coherence(T, T, _FS, _W, nperseg=512)
        assert coh > 0.9, f"Identical signals: coherence={coh:.3f}, expected > 0.9"

    def test_independent_signals_low_coherence(self):
        """SCENARIO-FP07-002: independent noise → coherence near zero."""
        rng = np.random.default_rng(1)
        T1 = rng.normal(0, 0.05, _N)
        T2 = rng.normal(0, 0.05, _N)
        coh = inter_thermistor_coherence(T1, T2, _FS, _W, nperseg=512)
        assert coh < 0.4, f"Independent signals: coherence={coh:.3f}, expected < 0.4"

    def test_coherence_in_unit_interval(self):
        """Coherence is always in [0, 1]."""
        rng = np.random.default_rng(2)
        T1 = rng.normal(0, 0.1, _N)
        T2 = rng.normal(0, 0.1, _N)
        coh = inter_thermistor_coherence(T1, T2, _FS, _W)
        assert 0.0 <= coh <= 1.0

    def test_partial_coherence(self):
        """Partially correlated signals → intermediate coherence."""
        rng = np.random.default_rng(3)
        shared = rng.normal(0, 0.05, _N)
        T1 = shared + rng.normal(0, 0.05, _N)
        T2 = shared + rng.normal(0, 0.05, _N)
        coh = inter_thermistor_coherence(T1, T2, _FS, _W, nperseg=512)
        assert 0.2 < coh < 0.9, f"Partial coherence={coh:.3f}"
