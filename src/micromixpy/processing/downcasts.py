"""Extract individual downcasts from a multi-profile VMP deployment file."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.signal import savgol_filter


@dataclass
class Downcast:
    """One downcast extracted from a .mat file."""

    profile_number: int

    # Fast-rate arrays (indices into parent MatData)
    t_fast: np.ndarray
    P_fast: np.ndarray
    W_fast: np.ndarray
    sh1: np.ndarray
    sh2: np.ndarray
    T1_fast: np.ndarray
    T2_fast: np.ndarray
    Ax: np.ndarray
    Ay: np.ndarray
    Chlorophyll: np.ndarray
    Turbidity: np.ndarray

    # Slow-rate arrays (interpolated or subset)
    t_slow: np.ndarray
    P_slow: np.ndarray
    W_slow: np.ndarray
    JAC_T: np.ndarray
    JAC_C: np.ndarray

    # Flags (same length as fast arrays)
    accel_flag: np.ndarray = field(default_factory=lambda: np.array([], dtype=bool))
    """True where profiler has not yet reached terminal velocity — flag for epsilon."""


def _smooth_W(W: np.ndarray, fs: float, tau: float = 1.5) -> np.ndarray:
    """Savitzky-Golay smooth of fall speed over a ~tau second window."""
    window = int(tau * fs)
    window += 1 - window % 2  # ensure odd
    window = max(window, 5)
    return savgol_filter(W, window_length=window, polyorder=3)


def _acceleration_flag(W_smooth: np.ndarray, frac: float = 0.90) -> np.ndarray:
    """Flag samples where profiler has not yet reached terminal velocity.

    Terminal velocity is taken as the median fall speed of the downcast.
    Samples before W first exceeds frac * W_terminal are flagged.
    """
    W_terminal = np.nanmedian(W_smooth)
    flag = np.zeros(len(W_smooth), dtype=bool)
    reached = np.argmax(W_smooth >= frac * W_terminal)
    if reached > 0:
        flag[:reached] = True
    return flag


def extract_downcasts(
    mat,  # MatData
    surface_threshold: float = 2.0,
    min_W: float = 0.05,
    min_depth: float = 10.0,
    min_duration_s: float = 10.0,
) -> list[Downcast]:
    """Extract all downcast segments from a MatData object.

    Parameters
    ----------
    surface_threshold : float
        Pressure (dbar) above which data is considered surface soak.
    min_W : float
        Minimum fall speed (m/s) to qualify as a downcast sample.
    min_depth : float
        Minimum maximum pressure (dbar) for a valid downcast.
    min_duration_s : float
        Minimum duration (seconds) for a valid downcast.
    """
    fs = mat.fs_fast
    P = mat.P_fast
    W = mat.W_fast

    W_smooth = _smooth_W(W, fs)

    # Downcast mask: below surface + actively falling
    dc_mask = (P > surface_threshold) & (W_smooth > min_W)

    # Label contiguous downcast segments
    transitions = np.diff(dc_mask.astype(int))
    starts = np.where(transitions == 1)[0] + 1
    ends = np.where(transitions == -1)[0] + 1

    if dc_mask[0]:
        starts = np.concatenate([[0], starts])
    if dc_mask[-1]:
        ends = np.concatenate([ends, [len(P)]])

    # Helper: extract slow-rate slice covering fast-rate time window
    def _slow_slice(t0: float, t1: float) -> tuple[slice, ...]:
        mask = (mat.t_slow >= t0) & (mat.t_slow <= t1)
        idx = np.where(mask)[0]
        if len(idx) == 0:
            return slice(0, 0)
        return slice(idx[0], idx[-1] + 1)

    downcasts: list[Downcast] = []
    profile_num = 0

    for i_start, i_end in zip(starts, ends):
        seg_P = P[i_start:i_end]
        seg_t = mat.t_fast[i_start:i_end]

        if seg_P.max() < min_depth:
            continue
        if (seg_t[-1] - seg_t[0]) < min_duration_s:
            continue

        profile_num += 1
        seg_W_smooth = W_smooth[i_start:i_end]
        accel = _acceleration_flag(seg_W_smooth)

        sl = _slow_slice(seg_t[0], seg_t[-1])

        downcasts.append(
            Downcast(
                profile_number=profile_num,
                t_fast=mat.t_fast[i_start:i_end],
                P_fast=mat.P_fast[i_start:i_end],
                W_fast=mat.W_fast[i_start:i_end],
                sh1=mat.sh1[i_start:i_end],
                sh2=mat.sh2[i_start:i_end],
                T1_fast=mat.T1_fast[i_start:i_end],
                T2_fast=mat.T2_fast[i_start:i_end],
                Ax=mat.Ax[i_start:i_end],
                Ay=mat.Ay[i_start:i_end],
                Chlorophyll=mat.Chlorophyll[i_start:i_end],
                Turbidity=mat.Turbidity[i_start:i_end],
                t_slow=mat.t_slow[sl],
                P_slow=mat.P_slow[sl],
                W_slow=mat.W_slow[sl],
                JAC_T=mat.JAC_T[sl],
                JAC_C=mat.JAC_C[sl],
                accel_flag=accel,
            )
        )

    return downcasts
