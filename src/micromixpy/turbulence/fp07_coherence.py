"""Dual-thermistor noise rejection via spectral coherence (REQ-FP07-001).

Two FP07 thermistors on the VMP-250 should measure the same temperature gradient
in real turbulence. Divergent spectra indicate noise contamination in one or both
probes. Mean squared coherence in the Batchelor fitting band provides a
segment-level quality flag.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import coherence as scipy_coherence

from .batchelor import K_BATCHELOR_MIN, K_BATCHELOR_MAX


def inter_thermistor_coherence(
    T1: np.ndarray,
    T2: np.ndarray,
    fs: float,
    W: float | np.ndarray,
    nperseg: int = 512,
    overlap: float = 0.5,
    k_min: float = K_BATCHELOR_MIN,
    k_max: float = K_BATCHELOR_MAX,
) -> float:
    """Mean squared coherence between T1 and T2 temperature gradient spectra.

    Computes the gradient of each thermistor's temperature record (dT/dt → dT/dz
    via fall speed), then estimates the squared coherence spectrum between them.
    Returns the mean coherence in the [k_min, k_max] wavenumber band.

    Parameters
    ----------
    T1, T2  : calibrated FP07 temperature arrays (°C) for one depth bin
    fs      : sampling rate (Hz)
    W       : mean fall speed for the bin (m/s); scalar or array
    nperseg : Welch segment length (samples)
    k_min   : lower wavenumber bound for coherence averaging (cpm)
    k_max   : upper wavenumber bound

    Returns
    -------
    mean_coh2 : mean squared coherence in [k_min, k_max]; scalar in [0, 1]
    """
    if np.ndim(W) > 0:
        W_mean = float(np.nanmean(W))
    else:
        W_mean = float(W)

    dt = 1.0 / fs
    dT1dz = np.gradient(T1, dt) / W_mean
    dT2dz = np.gradient(T2, dt) / W_mean

    noverlap = int(nperseg * overlap)
    f, coh2 = scipy_coherence(dT1dz, dT2dz, fs=fs, nperseg=nperseg, noverlap=noverlap)

    # Convert frequency axis to wavenumber and average in band
    k = f / W_mean
    band = (k >= k_min) & (k <= k_max)
    if band.sum() == 0:
        return float(np.mean(coh2))  # fallback: average all bins
    return float(np.mean(coh2[band]))
