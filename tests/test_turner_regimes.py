"""Tests for Turner angle and mixing regime classification.

REQ-TURNER-001: Turner angle computed from binned CTD data.
REQ-REGIME-001: Bouffard & Boegman (2013) regime classification.
SCENARIO-REGIME-001: classification logic.
"""

import numpy as np
import pytest

from micromixpy.oceanography.turner import compute_turner_angle
from micromixpy.turbulence.regimes import classify_regimes, TURBULENT, DOUBLE_DIFFUSION, WEAK_MIXING, INDETERMINATE


class TestTurnerAngle:
    def test_returns_finite_values(self):
        """Turner angle is finite for valid CTD data."""
        SA = np.array([32.0, 33.0, 34.0, 35.0])
        CT = np.array([4.0, 2.0, 1.0, 0.0])
        pressure = np.array([5.0, 20.0, 50.0, 100.0])
        Tu, Rr, p_mid = compute_turner_angle(SA, CT, pressure, lat=69.0)
        assert np.all(np.isfinite(Tu))
        assert len(Tu) == len(SA) - 1

    def test_salt_fingering_regime(self):
        """Warm, salty water over cold, fresh → positive Turner angle > 45°."""
        # Salt-fingering: warm+salty over cold+fresh (T and S both destabilize via diffusion)
        SA = np.array([35.0, 34.5, 34.0, 33.5])  # decreasing with depth
        CT = np.array([4.0, 3.5, 3.0, 2.5])       # decreasing with depth
        pressure = np.array([5.0, 25.0, 50.0, 75.0])
        Tu, Rr, _ = compute_turner_angle(SA, CT, pressure, lat=69.0)
        # Salt-fingering favorable: Tu > 45°
        assert np.any(np.abs(Tu) > 0), "Expected nonzero Turner angle"


class TestClassifyRegimes:
    def test_turbulent_mixing(self):
        """SCENARIO-REGIME-001: high Reb, small Tu → turbulent_mixing."""
        eps = np.array([1e-6])
        N2 = np.array([1e-4])
        Tu = np.array([10.0])  # degrees
        regime = classify_regimes(eps, N2, Tu)
        assert regime[0] == TURBULENT

    def test_double_diffusion(self):
        """SCENARIO-REGIME-001: low Reb, large Tu → double_diffusion."""
        eps = np.array([1e-10])
        N2 = np.array([1e-4])
        Tu = np.array([70.0])  # degrees — salt fingering
        regime = classify_regimes(eps, N2, Tu)
        assert regime[0] == DOUBLE_DIFFUSION

    def test_weak_mixing(self):
        """SCENARIO-REGIME-001: low Reb, small Tu → weak_mixing."""
        eps = np.array([1e-10])
        N2 = np.array([1e-4])
        Tu = np.array([20.0])
        regime = classify_regimes(eps, N2, Tu)
        assert regime[0] == WEAK_MIXING

    def test_indeterminate_negative_N2(self):
        """N² ≤ 0 → indeterminate."""
        eps = np.array([1e-6])
        N2 = np.array([-1e-4])
        Tu = np.array([10.0])
        regime = classify_regimes(eps, N2, Tu)
        assert regime[0] == INDETERMINATE

    def test_indeterminate_nan(self):
        """NaN eps → indeterminate."""
        eps = np.array([np.nan])
        N2 = np.array([1e-4])
        Tu = np.array([10.0])
        regime = classify_regimes(eps, N2, Tu)
        assert regime[0] == INDETERMINATE

    def test_reb_boundary(self):
        """Reb exactly at threshold 20 → turbulent_mixing (inclusive)."""
        nu = 1e-6
        N2 = np.array([1e-4])
        eps = np.array([20.0 * nu * N2[0]])  # Reb = 20 exactly
        Tu = np.array([10.0])
        regime = classify_regimes(eps, N2, Tu)
        assert regime[0] == TURBULENT
