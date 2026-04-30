"""Power spectral density of shear and temperature gradient signals."""

from __future__ import annotations

import numpy as np
from scipy.signal import welch


def shear_psd(
    shear: np.ndarray,
    fs: float,
    W: float | np.ndarray,
    nperseg: int = 4096,
    overlap: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute shear power spectral density in wavenumber space.

    Uses Welch's method to compute the frequency-domain PSD, then converts
    to wavenumber using Taylor's frozen-turbulence hypothesis: k = f / W.

    Parameters
    ----------
    shear   : physical shear (s^-1)
    fs      : sampling rate (Hz)
    W       : mean fall speed for the segment (m/s), scalar or array
              (if array, the mean is used)
    nperseg : samples per Welch segment
    overlap : fractional overlap between segments

    Returns
    -------
    k   : wavenumber array (cycles per metre, cpm)
    phi : shear variance PSD (s^-2 / cpm)
    """
    if np.ndim(W) > 0:
        W_mean = float(np.nanmean(W))
    else:
        W_mean = float(W)

    if W_mean <= 0:
        raise ValueError("Fall speed W must be positive for downcast data.")

    noverlap = int(nperseg * overlap)
    f, pxx = welch(shear, fs=fs, nperseg=nperseg, noverlap=noverlap, window="hann")

    # Convert from frequency to wavenumber: k = f / W, phi_k = phi_f * W
    k = f / W_mean
    phi = pxx * W_mean

    return k, phi


def temperature_gradient_psd(
    T_cal: np.ndarray,
    depth: np.ndarray,
    W: float | np.ndarray,
    fs: float,
    nperseg: int = 4096,
    overlap: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute temperature gradient PSD in wavenumber space.

    Computes dT/dz by numerical differentiation of the calibrated fast
    temperature with respect to depth, then applies Welch + Taylor hypothesis.

    Parameters
    ----------
    T_cal : calibrated fast temperature (°C)
    depth : depth (m or dbar) at fast rate
    W     : mean fall speed (m/s) for the segment
    fs    : fast sampling rate (Hz)
    """
    if np.ndim(W) > 0:
        W_mean = float(np.nanmean(W))
    else:
        W_mean = float(W)

    # dT/dz = (dT/dt) / W; pass explicit spacing to np.gradient to be robust
    # against any index-vs-physical-unit confusion.
    dt = 1.0 / fs  # seconds per sample
    dTdt = np.gradient(T_cal, dt)  # K/s — explicit spacing avoids silent breakage
    dTdz = dTdt / W_mean           # K/m

    return shear_psd(dTdz, fs=fs, W=W_mean, nperseg=nperseg, overlap=overlap)
