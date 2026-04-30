"""Despike optical backscatter (chlorophyll, turbidity) profiles."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import median_filter


def despike(
    signal: np.ndarray,
    window: int = 51,
    threshold: float = 3.0,
    replace: str = "median",
) -> np.ndarray:
    """Replace spikes with a rolling median.

    A sample is a spike if |signal - median| > threshold * MAD, where MAD is
    the median absolute deviation of the entire profile.

    Parameters
    ----------
    signal    : 1-D array to despike
    window    : half-window for the running median filter (samples)
    threshold : spike detection threshold in units of MAD
    replace   : 'median' replaces with local median; 'nan' sets to NaN

    Returns
    -------
    despiked signal (same shape as input)
    """
    out = signal.copy().astype(float)
    med = median_filter(out, size=window, mode="nearest")
    resid = out - med
    mad = np.nanmedian(np.abs(resid))
    # Fall back to std-based scale when MAD is zero (e.g., near-constant signal)
    if mad == 0:
        mad = np.nanstd(resid) * 0.6745  # consistent with Gaussian MAD
    if mad == 0:
        return out
    spike = np.abs(resid) > threshold * mad
    if replace == "median":
        out[spike] = med[spike]
    else:
        out[spike] = np.nan
    return out
