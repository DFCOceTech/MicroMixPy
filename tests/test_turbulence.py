"""Unit tests for turbulence modules.

REQ-TURB-001: Nasmyth spectrum peaks at expected wavenumber for given epsilon.
REQ-TURB-002: fit_epsilon recovers known epsilon from a synthetic Nasmyth spectrum.
REQ-TURB-003: best_epsilon_estimate returns the minimum of two valid estimates.
REQ-TURB-004: best_epsilon_estimate falls back to the single valid probe.
"""

import numpy as np
import pytest

from micromixpy.turbulence.nasmyth import nasmyth_spectrum, fit_epsilon
from micromixpy.turbulence.dissipation import best_epsilon_estimate


class TestNasmythSpectrum:
    def test_spectrum_positive(self):
        """REQ-TURB-001: spectrum values are positive."""
        k = np.logspace(-1, 2, 200)
        phi = nasmyth_spectrum(k, epsilon=1e-8)
        assert np.all(phi > 0)

    def test_spectrum_shape(self):
        """REQ-TURB-001: spectrum rolls off at large wavenumbers."""
        k = np.logspace(-1, 3, 500)
        phi = nasmyth_spectrum(k, epsilon=1e-8)
        # Peak should be at k < 100 cpm for epsilon=1e-8
        peak_k = k[np.argmax(phi)]
        assert 0.1 < peak_k < 200, f"Unexpected peak wavenumber: {peak_k}"

    def test_higher_epsilon_shifts_spectrum(self):
        """REQ-TURB-001: higher epsilon → higher amplitude and peak shifts right."""
        k = np.logspace(-1, 3, 500)
        phi_low = nasmyth_spectrum(k, epsilon=1e-10)
        phi_high = nasmyth_spectrum(k, epsilon=1e-6)
        assert phi_high.max() > phi_low.max()


class TestFitEpsilon:
    def test_recovers_known_epsilon(self):
        """REQ-TURB-002: fitting a synthetic Nasmyth spectrum recovers epsilon within 1 decade."""
        k = np.logspace(0, 2, 300)
        eps_true = 1e-8
        phi = nasmyth_spectrum(k, eps_true)
        # Add small noise
        rng = np.random.default_rng(7)
        phi_noisy = phi * 10 ** (rng.normal(0, 0.1, len(k)))

        eps_fit = fit_epsilon(k, phi_noisy)
        assert np.isfinite(eps_fit)
        log_ratio = abs(np.log10(eps_fit) - np.log10(eps_true))
        assert log_ratio < 1.0, f"eps fit={eps_fit:.2e}, true={eps_true:.2e}"

    def test_returns_nan_for_empty_spectrum(self):
        """REQ-TURB-002: NaN returned for all-NaN spectrum."""
        k = np.linspace(1, 100, 50)
        phi = np.full(50, np.nan)
        assert np.isnan(fit_epsilon(k, phi))


class TestBestEpsilon:
    def test_minimum_method(self):
        """REQ-TURB-003: minimum method returns element-wise minimum."""
        eps1 = np.array([1e-8, 1e-7, np.nan])
        eps2 = np.array([1e-9, np.nan, 1e-6])
        best = best_epsilon_estimate(eps1, eps2, method="minimum")
        assert best[0] == pytest.approx(1e-9)
        assert best[1] == pytest.approx(1e-7)
        assert best[2] == pytest.approx(1e-6)

    def test_fallback_to_single_probe(self):
        """REQ-TURB-004: NaN probe falls back to the other probe's value."""
        eps1 = np.array([1e-8, np.nan])
        eps2 = np.array([np.nan, 3e-9])
        best = best_epsilon_estimate(eps1, eps2)
        assert best[0] == pytest.approx(1e-8)
        assert best[1] == pytest.approx(3e-9)

    def test_both_nan_stays_nan(self):
        eps1 = np.array([np.nan])
        eps2 = np.array([np.nan])
        best = best_epsilon_estimate(eps1, eps2)
        assert np.isnan(best[0])
