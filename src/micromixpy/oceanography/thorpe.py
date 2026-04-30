"""Thorpe scale computation and thermohaline staircase detection."""

from __future__ import annotations

import numpy as np


def compute_thorpe_scales(
    density: np.ndarray,
    depth: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute Thorpe displacements and Thorpe scales from a density profile.

    The Thorpe scale Lt = rms(d) over each overturn, where d is the vertical
    displacement needed to sort the density profile to stable order.

    Parameters
    ----------
    density : potential density anomaly (kg/m³), may be non-monotonic
    depth   : depth (m or dbar), same length as density

    Returns
    -------
    thorpe_disp  : Thorpe displacement at each sample (m); NaN for invalid samples
    thorpe_scale : Thorpe scale (rms displacement) per sample (m); 0 outside overturns
    """
    n = len(density)
    thorpe_disp_out = np.zeros(n)
    thorpe_scale_out = np.zeros(n)

    valid = np.isfinite(density) & np.isfinite(depth)
    n_valid = valid.sum()
    if n_valid < 4:
        return thorpe_disp_out, thorpe_scale_out

    # Work only on valid samples to prevent NaN corruption in argsort
    d_v = density[valid]
    z_v = depth[valid]
    n_v = n_valid

    dz_median = float(np.median(np.abs(np.diff(z_v))))
    if dz_median == 0:
        return thorpe_disp_out, thorpe_scale_out

    # Sort valid density profile to stable order
    sorted_idx = np.argsort(d_v, kind="stable")
    # Inverse permutation: where does each original parcel end up?
    inverse_perm = np.empty(n_v, dtype=int)
    inverse_perm[sorted_idx] = np.arange(n_v)

    orig_pos = np.arange(n_v)
    thorpe_disp_v = (inverse_perm - orig_pos) * dz_median

    # Cumulative displacement — overturns are regions where cumsum ≠ 0
    cum_disp = np.cumsum(thorpe_disp_v)
    thorpe_scale_v = np.zeros(n_v)

    zero_crossings = np.where(np.diff(np.sign(cum_disp)))[0]
    boundaries = np.concatenate([[0], zero_crossings + 1, [n_v]])

    for i in range(len(boundaries) - 1):
        sl = slice(boundaries[i], boundaries[i + 1])
        seg_disp = thorpe_disp_v[sl]
        if np.any(seg_disp != 0):
            lt = np.sqrt(np.mean(seg_disp**2))
            thorpe_scale_v[sl] = lt

    # Scatter results back to full-length output arrays
    thorpe_disp_out[valid] = thorpe_disp_v
    thorpe_scale_out[valid] = thorpe_scale_v

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
