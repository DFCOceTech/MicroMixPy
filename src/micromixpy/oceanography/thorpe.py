"""Thorpe scale computation and thermohaline staircase detection."""

from __future__ import annotations

import warnings

import numpy as np
from mixsea.overturn import thorpe_scale as _mixsea_thorpe_scale

# Typical sigma0 noise floor for a JAC CTD (combined T/C uncertainty ~ 0.001 kg m⁻³)
_DEFAULT_DNOISE: float = 0.001


def compute_thorpe_scales(
    density: np.ndarray,
    depth: np.ndarray,
    dnoise: float = _DEFAULT_DNOISE,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute Thorpe displacements and Thorpe scales via mixsea.

    Wraps mixsea.overturn.thorpe_scale, which uses the intermediate-profile
    method and returns the Gargett & Garner overturn ratio alongside the
    standard Thorpe diagnostics.

    Parameters
    ----------
    density : potential density anomaly σ₀ (kg m⁻³)
    depth   : pressure or depth (dbar / m), monotonically increasing downward
    dnoise  : density noise floor (kg m⁻³); patches with density span < dnoise
              are treated as spurious and set to zero (default 0.001)

    Returns
    -------
    thorpe_disp  : Thorpe displacement at each sample (m)
    thorpe_scale : Thorpe scale Lt (rms displacement) per sample (m);
                   0 outside overturns or where patch is noise-flagged
    """
    n = len(density)
    thorpe_disp_out = np.zeros(n)
    thorpe_scale_out = np.zeros(n)

    valid = np.isfinite(density) & np.isfinite(depth)
    if valid.sum() < 4:
        return thorpe_disp_out, thorpe_scale_out

    d_v = density[valid]
    z_v = depth[valid]

    # Sort by depth if not monotonic (minor reversals from heave / attitude noise)
    sort_idx = np.argsort(z_v, kind="stable")
    inverse_sort = np.argsort(sort_idx, kind="stable")
    z_sorted = z_v[sort_idx]
    d_sorted = d_v[sort_idx]

    # mixsea raises ValueError when q[0] > q[-1] (entire profile unstable)
    if d_sorted[0] >= d_sorted[-1]:
        return thorpe_disp_out, thorpe_scale_out

    try:
        Lt, thorpe_disp_v, _, noise_flag, _, _, _, _ = _mixsea_thorpe_scale(
            z_sorted, d_sorted, dnoise
        )
    except Exception as exc:
        warnings.warn(f"mixsea thorpe_scale failed: {exc}; returning zeros.")
        return thorpe_disp_out, thorpe_scale_out

    # Zero out noise-flagged patches (density span < dnoise → likely spurious)
    Lt[noise_flag] = 0.0
    # mixsea returns NaN for non-overturn regions; convert to 0
    Lt = np.where(np.isfinite(Lt), Lt, 0.0)

    # Map sorted results back to original index order
    thorpe_disp_out[valid] = thorpe_disp_v[inverse_sort]
    thorpe_scale_out[valid] = Lt[inverse_sort]

    return thorpe_disp_out, thorpe_scale_out


def detect_staircases(
    T_fast: np.ndarray,
    depth_fast: np.ndarray,
    min_step: float = 0.05,
    min_layer_m: float = 0.5,
    smooth_dz: float = 0.1,
) -> np.ndarray:
    """Flag depth indices that belong to thermohaline staircase layers.

    Identifies alternating mixed layers and sharp interfaces in the fast
    temperature profile characteristic of double-diffusive staircases.

    Parameters
    ----------
    T_fast      : calibrated FP07 temperature (°C) at fast rate
    depth_fast  : depth (m or dbar) at fast rate
    min_step    : minimum temperature step across an interface (°C)
    min_layer_m : minimum thickness of a mixed layer (m)
    smooth_dz   : vertical scale for smoothing before gradient detection (m)

    Returns
    -------
    staircase_flag : boolean array, True where temperature staircase is detected
    """
    flag = np.zeros(len(T_fast), dtype=bool)
    valid = np.isfinite(T_fast) & np.isfinite(depth_fast)
    if valid.sum() < 10:
        return flag

    dz_bin = smooth_dz
    z_edges = np.arange(depth_fast[valid].min(), depth_fast[valid].max() + dz_bin, dz_bin)
    z_mid = 0.5 * (z_edges[:-1] + z_edges[1:])
    T_binned = np.full(len(z_mid), np.nan)
    for j, (z0, z1) in enumerate(zip(z_edges[:-1], z_edges[1:])):
        sel = valid & (depth_fast >= z0) & (depth_fast < z1)
        if sel.sum() > 0:
            T_binned[j] = np.nanmean(T_fast[sel])

    dTdz = np.gradient(T_binned, z_mid)
    interface_mask = np.abs(dTdz) > min_step / dz_bin
    layer_mask = ~interface_mask

    transitions = np.diff(layer_mask.astype(int))
    starts = np.where(transitions == 1)[0] + 1
    ends = np.where(transitions == -1)[0] + 1
    if layer_mask[0]:
        starts = np.concatenate([[0], starts])
    if layer_mask[-1]:
        ends = np.concatenate([ends, [len(layer_mask)]])

    staircase_z_ranges = []
    for s, e in zip(starts, ends):
        thickness = z_mid[e - 1] - z_mid[s]
        if thickness >= min_layer_m:
            staircase_z_ranges.append((z_mid[s], z_mid[e - 1]))

    for z0, z1 in staircase_z_ranges:
        flag |= (depth_fast >= z0) & (depth_fast <= z1)

    return flag
