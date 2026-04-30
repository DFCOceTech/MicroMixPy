"""Calibrate FP07 fast thermistors against the JAC-T reference sensor."""

from __future__ import annotations

import numpy as np
from scipy.interpolate import interp1d


def calibrate_fp07(
    T_fast: np.ndarray,
    t_fast: np.ndarray,
    T_jac: np.ndarray,
    t_slow: np.ndarray,
) -> np.ndarray:
    """Calibrate a FP07 temperature record against the JAC-T reference.

    Fits a linear regression T_cal = gain * T_fast + offset using the JAC-T
    interpolated to the fast time base, then returns the calibrated series.

    Parameters
    ----------
    T_fast : fast-rate FP07 temperature (°C), already converted to °C by ODAS
    t_fast : fast-rate time vector (s)
    T_jac  : JAC-T temperature (°C) at slow rate
    t_slow : slow-rate time vector (s)

    Returns
    -------
    T_cal : calibrated FP07 temperature at fast rate (°C)
    """
    interp = interp1d(t_slow, T_jac, bounds_error=False, fill_value="extrapolate")
    T_ref = interp(t_fast)

    valid = np.isfinite(T_fast) & np.isfinite(T_ref)
    if valid.sum() < 10:
        return T_fast.copy()

    coef = np.polyfit(T_fast[valid], T_ref[valid], 1)
    return coef[0] * T_fast + coef[1]
