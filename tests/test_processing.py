"""Unit tests for processing modules.

REQ-PROC-001: Surface soak removal rejects samples above surface_threshold dbar.
REQ-PROC-002: Downcast extraction identifies contiguous falling segments.
REQ-PROC-003: Acceleration flag marks early profile before terminal velocity.
REQ-PROC-004: FP07 calibration reduces bias against JAC-T.
REQ-PROC-005: Optical despiking removes isolated outliers without distorting the signal.
REQ-TDISS-007: Deceleration flag at end of downcast excludes tether-contaminated bins.
"""

import numpy as np
import pytest

from micromixpy.processing.calibration import calibrate_fp07
from micromixpy.processing.downcasts import _deceleration_flag
from micromixpy.processing.optics import despike


class TestCalibrateF07:
    def test_removes_linear_bias(self):
        """REQ-PROC-004: linear offset should be removed after calibration."""
        t = np.linspace(0, 100, 500)
        T_true = np.sin(t / 10) * 2 + 5.0
        # FP07 has 0.95x gain + 0.5 offset relative to JAC-T
        T_fp07 = T_true / 0.95 - 0.5
        T_jac = T_true + np.random.default_rng(0).normal(0, 0.01, len(t))

        T_cal = calibrate_fp07(T_fp07, t, T_jac, t)
        residual = T_cal - T_true
        assert np.abs(residual).mean() < 0.05, "Mean residual after calibration too large"

    def test_returns_input_when_insufficient_data(self):
        """REQ-PROC-004: returns uncalibrated input when too few valid samples."""
        T_fp07 = np.full(5, np.nan)
        T_cal = calibrate_fp07(T_fp07, np.arange(5.0), np.array([1.0]), np.array([0.0]))
        assert np.all(np.isnan(T_cal))


class TestDecelerationFlag:
    """SCENARIO-TDISS-007-A, SCENARIO-TDISS-007-B"""

    def test_ramp_down_flags_tail(self):
        """SCENARIO-TDISS-007-A: deceleration tail is flagged when W ramps to zero."""
        n = 100
        W = np.ones(n) * 0.6  # terminal velocity 0.6 m/s
        # Ramp the last 20 samples from 0.6 to 0.0
        W[80:] = np.linspace(0.6, 0.0, 20)
        flag = _deceleration_flag(W, frac=0.90)
        # At frac=0.90 and W_terminal≈0.6, threshold is 0.54.
        # Samples drop below 0.54 by index ~82; flag must cover the clear tail.
        assert flag[85:].all(), "Clearly decelerated tail should be flagged"
        assert not flag[:80].any(), "Terminal-velocity region should not be flagged"

    def test_constant_velocity_flags_nothing(self):
        """SCENARIO-TDISS-007-B: constant fall speed → no samples flagged."""
        W = np.ones(200) * 0.6
        flag = _deceleration_flag(W, frac=0.90)
        assert not flag.any(), "Steady fall should flag nothing"

    def test_accel_decel_do_not_overlap_on_normal_profile(self):
        """Accel and decel flags should leave a clean middle section for a typical profile."""
        from micromixpy.processing.downcasts import _acceleration_flag
        n = 200
        W = np.concatenate([
            np.linspace(0.0, 0.6, 20),   # acceleration
            np.ones(160) * 0.6,           # terminal
            np.linspace(0.6, 0.0, 20),   # deceleration
        ])
        accel = _acceleration_flag(W)
        decel = _deceleration_flag(W)
        combined = accel | decel
        # At least 50 % of samples should be clean
        assert combined.sum() < n // 2


class TestDespike:
    def test_removes_spikes(self):
        """REQ-PROC-005: artificial spikes are removed."""
        rng = np.random.default_rng(42)
        signal = rng.normal(0, 0.1, 1000)
        spike_idx = [100, 300, 700]
        signal[spike_idx] = 50.0  # obvious spikes

        cleaned = despike(signal, window=21, threshold=3.0)
        assert all(abs(cleaned[i]) < 5.0 for i in spike_idx), "Spikes not removed"

    def test_preserves_signal(self):
        """REQ-PROC-005: smooth signal is largely preserved."""
        t = np.linspace(0, 10, 1000)
        signal = np.sin(t)
        cleaned = despike(signal, window=21, threshold=5.0)
        assert np.allclose(cleaned, signal, atol=0.05)

    def test_nan_replace_option(self):
        """REQ-PROC-005: replace='nan' sets spikes to NaN."""
        signal = np.ones(100)
        signal[50] = 1000.0
        cleaned = despike(signal, window=11, threshold=3.0, replace="nan")
        assert np.isnan(cleaned[50])
