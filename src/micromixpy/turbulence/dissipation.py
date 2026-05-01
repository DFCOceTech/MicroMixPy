"""Compute epsilon (TKE dissipation) and chi (thermal variance dissipation) profiles."""

from __future__ import annotations

import numpy as np

from .nasmyth import fit_epsilon
from .spectra import shear_psd, temperature_gradient_psd
from .batchelor import fit_batchelor
from .fp07_coherence import inter_thermistor_coherence

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
    exclude_above_dbar: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute epsilon profile from one shear probe using Nasmyth spectral fitting.

    Segments the downcast into depth bins, computes the shear PSD in each bin,
    and fits the Nasmyth spectrum iteratively.

    Parameters
    ----------
    shear              : physical shear (s^-1) — already calibrated by ODAS quicklook
    P                  : pressure (dbar) at fast rate
    W                  : fall speed (m/s) at fast rate
    fs                 : fast sampling rate (Hz)
    accel_flag         : boolean mask — True where terminal velocity not yet reached
    dz                 : depth bin size (dbar) for epsilon segmentation
    nu                 : kinematic viscosity (m²/s)
    nperseg            : Welch segment length (samples)
    exclude_above_dbar : bins with center pressure ≤ this value are set to NaN.
                         Use to exclude ship-hull-generated turbulence near the surface.
                         Default 0.0 (no exclusion). Units: dbar (≈ m for shallow water).

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
        if centers[j] <= exclude_above_dbar:
            continue  # leave NaN — ship-hull turbulence exclusion zone

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
    exclude_above_dbar: float = 0.0,
    method: str = "batchelor",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute chi (thermal variance dissipation) profile from calibrated temperature.

    Two methods are available via the `method` parameter:

    - 'batchelor' (default): Fit the Batchelor (1959) spectral shape to the
      observed temperature gradient PSD. Returns both chi and an independent
      epsilon estimate (eps_batchelor) from the Batchelor rolloff wavenumber.
      eps_batchelor is NaN when the rolloff wavenumber exceeds 50% of Nyquist.

    - 'direct': Integrate the observed PSD directly:
      chi = 6 · κ_T · ∫ Φ_dT/dz dk.  eps_batchelor is all NaN.

    Parameters
    ----------
    T_cal              : calibrated fast temperature (°C)
    P                  : pressure (dbar) at fast rate
    W                  : fall speed (m/s) at fast rate
    fs                 : fast sampling rate (Hz)
    dz                 : depth bin size for segmentation (dbar)
    exclude_above_dbar : bins with center pressure ≤ this value are set to NaN
    method             : 'batchelor' (default) or 'direct'

    Returns
    -------
    depth_chi     : bin-center depths (dbar)
    chi           : thermal variance dissipation (K²/s)
    eps_batchelor : TKE dissipation from Batchelor k_B (W/kg); NaN for 'direct'
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
    eps_batchelor = np.full(n_bins, np.nan)
    min_samples = max(64, nperseg // 2)

    for j, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
        if centers[j] <= exclude_above_dbar:
            continue  # leave NaN — ship-hull turbulence exclusion zone

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
            k, phi_dTdz = temperature_gradient_psd(
                T_seg, P[seg_clean], W_seg, fs, nperseg=nperseg_use
            )
            valid = np.isfinite(phi_dTdz) & (phi_dTdz > 0)
            if valid.sum() < 5:
                continue

            if method == "batchelor":
                k_nyquist = float(k[-1])
                chi_fit, eps_fit = fit_batchelor(
                    k[valid], phi_dTdz[valid], k_nyquist=k_nyquist, kappa_T=kappa_T
                )
                chi[j] = chi_fit
                eps_batchelor[j] = eps_fit
            else:
                chi[j] = 6.0 * kappa_T * float(np.trapezoid(phi_dTdz[valid], k[valid]))
        except Exception:
            pass

    return centers, chi, eps_batchelor


def compute_chi_profiles_dual(
    T1_cal: np.ndarray,
    T2_cal: np.ndarray,
    P: np.ndarray,
    W: np.ndarray,
    fs: float,
    accel_flag: np.ndarray | None = None,
    dz: float = 2.0,
    kappa_T: float = _KAPPA_T,
    nperseg: int = 512,
    exclude_above_dbar: float = 0.0,
    method: str = "batchelor",
    coherence_threshold: float = 0.5,
) -> dict[str, np.ndarray]:
    """Compute chi from both FP07 thermistors with inter-thermistor coherence rejection.

    Processes T1 and T2 separately, then flags bins where the two temperature
    gradient spectra are incoherent (REQ-FP07-001). Returns raw chi (before
    flagging), coherence-masked chi, and a best-estimate chi.

    Parameters
    ----------
    T1_cal, T2_cal      : calibrated FP07 temperatures (°C) at fast rate
    P                   : pressure (dbar) at fast rate
    W                   : fall speed (m/s) at fast rate
    fs                  : fast sampling rate (Hz)
    coherence_threshold : mean squared coherence threshold in fitting band;
                          bins below this are flagged (default 0.5)

    Returns
    -------
    dict with keys:
      depth      : bin-center depths (dbar)
      chi1_raw   : chi from T1 (before coherence masking)
      chi2_raw   : chi from T2
      chi1       : chi1_raw with low-coherence bins set to NaN
      chi2       : chi2_raw with low-coherence bins set to NaN
      eps_batchelor1, eps_batchelor2 : Batchelor epsilon from each probe
      coherence  : mean inter-thermistor coherence² per bin
      chi_flag   : True where bin failed coherence check
      chi_best   : log-mean of passing chi1, chi2; single probe when only one passes
    """
    # Compute chi for each thermistor independently
    depth, chi1_raw, eps_b1 = compute_chi_profile(
        T1_cal, P, W, fs,
        accel_flag=accel_flag, dz=dz, kappa_T=kappa_T, nperseg=nperseg,
        exclude_above_dbar=exclude_above_dbar, method=method,
    )
    _, chi2_raw, eps_b2 = compute_chi_profile(
        T2_cal, P, W, fs,
        accel_flag=accel_flag, dz=dz, kappa_T=kappa_T, nperseg=nperseg,
        exclude_above_dbar=exclude_above_dbar, method=method,
    )

    n_bins = len(depth)
    coherence = np.full(n_bins, np.nan)
    chi_flag = np.zeros(n_bins, dtype=bool)

    if accel_flag is None:
        accel_flag = np.zeros(len(P), dtype=bool)

    P_min = np.nanmin(P)
    P_max = np.nanmax(P)
    edges = np.arange(P_min, P_max + dz, dz)
    min_samples = max(64, nperseg // 2)

    for j, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
        if depth[j] <= exclude_above_dbar:
            continue
        seg = (P >= lo) & (P < hi) & np.isfinite(T1_cal) & np.isfinite(T2_cal) & (W > 0.05)
        seg_clean = seg & ~accel_flag
        if seg_clean.sum() < min_samples:
            continue
        nperseg_use = min(nperseg, seg_clean.sum() // 2)
        if nperseg_use < 64:
            continue
        try:
            coh = inter_thermistor_coherence(
                T1_cal[seg_clean], T2_cal[seg_clean],
                fs=fs, W=float(np.nanmean(W[seg_clean])),
                nperseg=nperseg_use,
            )
            coherence[j] = coh
            if coh < coherence_threshold:
                chi_flag[j] = True
        except Exception:
            pass

    # Apply coherence mask (REQ-FP07-002)
    chi1 = chi1_raw.copy()
    chi2 = chi2_raw.copy()
    chi1[chi_flag] = np.nan
    chi2[chi_flag] = np.nan

    # chi_best: log-mean of passing probes (REQ-FP07-003)
    chi_best = np.full(n_bins, np.nan)
    both = np.isfinite(chi1) & np.isfinite(chi2) & (chi1 > 0) & (chi2 > 0)
    only1 = np.isfinite(chi1) & (chi1 > 0) & ~np.isfinite(chi2)
    only2 = np.isfinite(chi2) & (chi2 > 0) & ~np.isfinite(chi1)
    chi_best[both] = np.exp(0.5 * (np.log(chi1[both]) + np.log(chi2[both])))
    chi_best[only1] = chi1[only1]
    chi_best[only2] = chi2[only2]

    return {
        "depth": depth,
        "chi1_raw": chi1_raw,
        "chi2_raw": chi2_raw,
        "chi1": chi1,
        "chi2": chi2,
        "eps_batchelor1": eps_b1,
        "eps_batchelor2": eps_b2,
        "coherence": coherence,
        "chi_flag": chi_flag,
        "chi_best": chi_best,
    }


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
