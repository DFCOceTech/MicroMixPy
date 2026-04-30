"""Bin profiler data to a uniform depth grid."""

from __future__ import annotations

import numpy as np


def bin_to_grid(
    variables: dict[str, np.ndarray],
    depth: np.ndarray,
    dz: float = 0.25,
    stat: str = "mean",
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Bin one or more variables to a uniform depth grid.

    Parameters
    ----------
    variables : mapping of name → 1-D array, all same length as depth
    depth     : depth (dbar or m) for each sample
    dz        : bin width (same units as depth); default 0.25 m
    stat      : aggregation statistic — 'mean' or 'median'

    Returns
    -------
    z_bin   : bin-center depths
    binned  : dict of name → binned array (NaN where bin is empty)
    """
    valid_depth = depth[np.isfinite(depth)]
    if len(valid_depth) == 0:
        return np.array([]), {k: np.array([]) for k in variables}

    z_min = np.floor(valid_depth.min() / dz) * dz
    z_max = np.ceil(valid_depth.max() / dz) * dz
    edges = np.arange(z_min, z_max + dz, dz)
    centers = 0.5 * (edges[:-1] + edges[1:])
    n_bins = len(centers)

    binned: dict[str, np.ndarray] = {}
    for name, arr in variables.items():
        result = np.full(n_bins, np.nan)
        for j, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
            sel = (depth >= lo) & (depth < hi) & np.isfinite(arr)
            if sel.sum() > 0:
                result[j] = np.nanmean(arr[sel]) if stat == "mean" else np.nanmedian(arr[sel])
        binned[name] = result

    return centers, binned
