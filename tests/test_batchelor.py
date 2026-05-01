"""Unit tests for Batchelor spectrum fitting.

REQ-TDISS-005: fit_batchelor recovers chi from synthetic spectrum.
REQ-TDISS-006: eps_batchelor is NaN when k_B > 0.5 * k_Nyquist.
SCENARIO-TDISS-005-A: chi within 0.5 log-decades of true value.
SCENARIO-TDISS-005-B: eps_batchelor NaN above Nyquist cutoff.
"""

import numpy as np
import pytest

from micromixpy.turbulence.batchelor import (
    batchelor_wavenumber,
    batchelor_spectrum,
    fit_batchelor,
)


_NU = 1e-6
_KAPPA_T = 1.4e-7
_Q = 3.7


class TestBatchelorWavenumber:
    def test_increases_with_epsilon(self):
        """Higher epsilon → larger Batchelor wavenumber."""
        k1 = batchelor_wavenumber(1e-9, _NU, _KAPPA_T)
        k2 = batchelor_wavenumber(1e-6, _NU, _KAPPA_T)
        assert k2 > k1

    def test_quarter_power_scaling(self):
        """k_B scales as eps^(1/4)."""
        k1 = batchelor_wavenumber(1e-8, _NU, _KAPPA_T)
        k2 = batchelor_wavenumber(1e-4, _NU, _KAPPA_T)
        # 1e-4 / 1e-8 = 1e4 → k_B ratio = 1e4^(1/4) = 10
        assert abs(k2 / k1 - 10.0) < 0.01


class TestBatchelorSpectrum:
    def test_positive_everywhere(self):
        k = np.linspace(0.5, 200, 500)
        phi = batchelor_spectrum(k, chi=1e-8, eps=1e-8)
        assert np.all(phi > 0)

    def test_integrates_to_chi_over_6kappaT(self):
        """SCENARIO-TDISS-005-A partial: integral of spectrum = chi/(6*kappa_T)."""
        chi_true = 1e-8
        eps = 1e-8
        k = np.linspace(0.01, 2000, 100_000)
        phi = batchelor_spectrum(k, chi=chi_true, eps=eps)
        integral = np.trapezoid(phi, k)
        expected = chi_true / (6 * _KAPPA_T)
        assert abs(integral / expected - 1.0) < 0.01, (
            f"Integral {integral:.3e} ≠ chi/(6*kT) {expected:.3e}"
        )

    def test_peak_at_correct_wavenumber(self):
        """Peak of Batchelor spectrum is at k_B / sqrt(2*q)."""
        eps = 1e-8
        k_B = batchelor_wavenumber(eps, _NU, _KAPPA_T)
        k_peak_expected = k_B / np.sqrt(2 * _Q)
        k = np.linspace(0.1, k_B * 3, 10_000)
        phi = batchelor_spectrum(k, chi=1e-8, eps=eps)
        k_peak_observed = k[np.argmax(phi)]
        assert abs(k_peak_observed / k_peak_expected - 1.0) < 0.02


class TestFitBatchelor:
    def test_recovers_chi(self):
        """SCENARIO-TDISS-005-A: fitted chi within 0.5 log-decades of true value."""
        chi_true = 1e-8
        eps_true = 1e-8
        k = np.linspace(0.5, 300, 500)
        k_nyquist = k[-1]
        phi = batchelor_spectrum(k, chi=chi_true, eps=eps_true)
        # Add small noise
        rng = np.random.default_rng(42)
        phi_noisy = phi * 10 ** (rng.normal(0, 0.05, len(k)))

        chi_fit, eps_fit = fit_batchelor(k, phi_noisy, k_nyquist)
        assert np.isfinite(chi_fit)
        assert abs(np.log10(chi_fit) - np.log10(chi_true)) < 0.5

    def test_recovers_eps(self):
        """Fitted eps within 1 log-decade (eps fitting is noisier than chi)."""
        chi_true = 1e-8
        eps_true = 1e-8
        k = np.linspace(0.5, 300, 500)
        k_nyquist = k[-1]
        phi = batchelor_spectrum(k, chi=chi_true, eps=eps_true)

        chi_fit, eps_fit = fit_batchelor(k, phi, k_nyquist)
        assert np.isfinite(eps_fit)
        assert abs(np.log10(eps_fit) - np.log10(eps_true)) < 1.0

    def test_eps_nan_above_nyquist_cutoff(self):
        """REQ-TDISS-006: eps_batchelor=NaN when k_B > 0.5*k_Nyquist."""
        # Use high eps so k_B >> Nyquist
        eps_high = 1e-3  # k_B ≈ 7400 cpm >> 400 cpm Nyquist
        chi_true = 1e-8
        k_nyquist = 400.0
        k = np.linspace(0.5, k_nyquist, 300)
        phi = batchelor_spectrum(k, chi=chi_true, eps=eps_high)

        chi_fit, eps_fit = fit_batchelor(k, phi, k_nyquist)
        assert np.isnan(eps_fit), "eps_batchelor should be NaN when k_B > 0.5*Nyquist"

    def test_returns_nan_for_invalid_input(self):
        """NaN or all-zero spectrum returns NaN."""
        k = np.linspace(1, 100, 50)
        chi, eps = fit_batchelor(k, np.full(50, np.nan), k_nyquist=100.0)
        assert np.isnan(chi) and np.isnan(eps)

    def test_returns_nan_for_fewer_than_5_valid_points(self):
        """< 5 valid points → (nan, nan)."""
        k = np.array([1.0, 2.0, 3.0, 4.0])
        phi = np.array([1e-8, 1e-9, 1e-10, 1e-11])
        chi, eps = fit_batchelor(k, phi, k_nyquist=100.0)
        assert np.isnan(chi) and np.isnan(eps)

    def test_k_zero_is_silently_excluded(self):
        """k=0 (DC component) is handled without error via the valid mask."""
        # Use eps=1e-9 so k_B≈76 cpm << 0.5*600=300 cpm (Nyquist cutoff not triggered)
        k = np.linspace(0.0, 600.0, 600)
        phi = batchelor_spectrum(np.maximum(k, 0.01), chi=1e-8, eps=1e-9)
        chi_fit, eps_fit = fit_batchelor(k, phi, k_nyquist=600.0)
        assert np.isfinite(chi_fit), "k=0 should be excluded silently, fit should succeed"

    def test_chi_nan_when_kB_near_nyquist(self):
        """REQ-TDISS-006: both chi and eps are NaN when k_B unresolved."""
        eps_high = 1e-3  # k_B >> Nyquist
        k = np.linspace(0.5, 400.0, 300)
        phi = batchelor_spectrum(k, chi=1e-8, eps=eps_high)
        chi_fit, eps_fit = fit_batchelor(k, phi, k_nyquist=400.0)
        assert np.isnan(eps_fit)
        assert np.isnan(chi_fit)

    def test_direct_method_chi_consistent(self):
        """Direct integration chi ≈ Batchelor-fit chi on a clean spectrum."""
        chi_true = 1e-8
        eps_true = 1e-8
        k = np.linspace(0.5, 300, 500)
        phi = batchelor_spectrum(k, chi=chi_true, eps=eps_true)

        chi_direct = 6 * _KAPPA_T * float(np.trapezoid(phi, k))
        chi_fit, _ = fit_batchelor(k, phi, k_nyquist=300.0)

        # Both should agree with true value within 0.5 decades
        assert abs(np.log10(chi_direct) - np.log10(chi_true)) < 0.5
        assert abs(np.log10(chi_fit) - np.log10(chi_true)) < 0.5
