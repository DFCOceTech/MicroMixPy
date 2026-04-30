"""Compute epsilon (TKE dissipation) and chi (thermal variance dissipation) profiles."""

from __future__ import annotations

import numpy as np

from .nasmyth import fit_epsilon
from .spectra import shear_psd, temperature_gradient_psd

_NU = 1.0e-6     # kinematic viscosity (m²/s)
_KAPPA_T = 1.4e-7  # thermal diffusivity (m²/s)


def compute_epsilon_profile(
    shear: np.ndarray,
    P: np.ndarray,
    W: np.ndarray,
    fs: float,
    accel_flag: np.ndarray | None = None,
    dz: float = 2.0,
    nu: float = _NU,
    nperseg: int = 512,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute epsilon profile from one shear probe using Nasmyth spectral fitting.

    Segments the downcast into depth bins, computes the shear PSD in each bin,
    and fits the Nasmyth spectrum iteratively.

    Parameters
    ----------
    shear      : physical shear (s^-1) — already calibrated by ODAS quicklook
    P          : pressure (dbar) at fast rate
    W          : fall speed (m/s) at fast rate
    fs         : fast sampling rate (Hz)
    accel_flag : boolean mask — True where terminal velocity not yet reached
    dz         : depth bin size (dbar) for epsilon segmentation
    nu         : kinematic viscosity (m²/s)
    nperseg    : Welch segment length (samples)

    Returns
    -------
    depth_eps : bin-center depths (dbar)
    epsilon   : dissipation rate (W/kg), NaN for flagged/invalid bins
    flag_accel: True where bin is contaminated by acceleration
    """
    if accel_flag is None:
        accel_flag = np.zeros(len(P), dtype=bool)
    if len(accel_flag) != len(P):
        raise ValueError(
            f"accel_flag length ({len(accel_flag)}) must match P length ({len(P)}). "
            "Pass a per-downcast flag, not a full-file flag."
        )

    P_min = np.nanmin(P)
    P_max = np.nanmax(P)
    edges = np.arange(P_min, P_max + dz, dz)
    centers = 0.5 * (edges[:-1] + edges[1:])
    n_bins = len(centers)

    depth_eps = centers
    epsilon = np.full(n_bins, np.nan)
    flag_out = np.zeros(n_bins, dtype=bool)

    min_samples = max(64, nperseg // 2)

    for j, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
        seg = (P >= lo) & (P < hi) & np.isfinite(shear) & (W > 0.05)
        if accel_flag[seg].any():
            flag_out[j] = True

        seg_clean = seg & ~accel_flag
        if seg_clean.sum() < min_samples:
            continue

        sh_seg = shear[seg_clean]
        W_seg = W[seg_clean]
        nperseg_use = min(nperseg, len(sh_seg) // 2)
        if nperseg_use < 64:
            continue

        try:
            k, phi = shear_psd(sh_seg, fs=fs, W=W_seg, nperseg=nperseg_use)
            if np.all(~np.isfinite(phi)):
                continue
            epsilon[j] = fit_epsilon(k, phi, nu=nu)
        except Exception:
            pass

    return depth_eps, epsilon, flag_out


def compute_chi_profile(
    T_cal: np.ndarray,
    P: np.ndarray,
    W: np.ndarray,
    fs: float,
    accel_flag: np.ndarray | None = None,
    dz: float = 2.0,
    kappa_T: float = _KAPPA_T,
    nperseg: int = 512,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute chi (thermal variance dissipation) profile from calibrated temperature.

    chi = 6 * kappa_T * integral(phi_dT/dz dk)

    Parameters
    ----------
    T_cal  : calibrated fast temperature (°C)
    P      : pressure (dbar) at fast rate
    W      : fall speed (m/s) at fast rate
    fs     : fast sampling rate (Hz)
    dz     : depth bin size for segmentation

    Returns
    -------
    depth_chi : bin-center depths (dbar)
    chi       : thermal variance dissipation (K²/s)
    """
    if accel_flag is None:
        accel_flag = np.zeros(len(P), dtype=bool)
    if len(accel_flag) != len(P):
        raise ValueError(
            f"accel_flag length ({len(accel_flag)}) must match P length ({len(P)})."
        )

    P_min = np.nanmin(P)
    P_max = np.nanmax(P)
    edges = np.arange(P_min, P_max + dz, dz)
    centers = 0.5 * (edges[:-1] + edges[1:])
    n_bins = len(centers)

    chi = np.full(n_bins, np.nan)
    min_samples = max(64, nperseg // 2)

    for j, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
        seg = (P >= lo) & (P < hi) & np.isfinite(T_cal) & (W > 0.05)
        seg_clean = seg & ~accel_flag
        if seg_clean.sum() < min_samples:
            continue

        T_seg = T_cal[seg_clean]
        W_seg = W[seg_clean]
        nperseg_use = min(nperseg, len(T_seg) // 2)
        if nperseg_use < 64:
            continue

        try:
            k, phi_dTdz = temperature_gradient_psd(T_seg, P[seg_clean], W_seg, fs, nperseg=nperseg_use)
            valid = np.isfinite(phi_dTdz)
            if valid.sum() < 3:
                continue
            chi[j] = 6.0 * kappa_T * float(np.trapezoid(phi_dTdz[valid], k[valid]))
        except Exception:
            pass

    return centers, chi


def best_epsilon_estimate(
    eps1: np.ndarray,
    eps2: np.ndarray,
    method: str = "minimum",
) -> np.ndarray:
    """Combine epsilon from two shear probes into a best estimate.

    Parameters
    ----------
    eps1, eps2 : epsilon profiles from shear probes 1 and 2 (same length)
    method     : 'minimum' takes the lower value (less-contaminated probe);
                 'mean' takes the log-mean of valid estimates

    Returns
    -------
    eps_best : best-estimate epsilon array
    """
    eps_best = np.full(len(eps1), np.nan)
    both_valid = np.isfinite(eps1) & np.isfinite(eps2)
    only1 = np.isfinite(eps1) & ~np.isfinite(eps2)
    only2 = np.isfinite(eps2) & ~np.isfinite(eps1)

    if method == "minimum":
        eps_best[both_valid] = np.minimum(eps1[both_valid], eps2[both_valid])
    else:  # log-mean
        eps_best[both_valid] = np.exp(
            0.5 * (np.log(eps1[both_valid]) + np.log(eps2[both_valid]))
        )

    eps_best[only1] = eps1[only1]
    eps_best[only2] = eps2[only2]
    return eps_best
