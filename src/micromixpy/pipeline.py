"""End-to-end processing pipeline for a single VMP downcast."""

from __future__ import annotations

from typing import Any

import gsw
import numpy as np
from scipy.interpolate import interp1d

from .processing.calibration import calibrate_fp07
from .processing.downcasts import Downcast
from .processing.optics import despike
from .oceanography.properties import compute_ct_sa_density, compute_N2
from .oceanography.thorpe import compute_thorpe_scales, detect_staircases
from .oceanography.binning import bin_to_grid
from .oceanography.turner import compute_turner_angle
from .turbulence.dissipation import (
    compute_epsilon_profile,
    compute_chi_profiles_dual,
    best_epsilon_estimate,
)
from .turbulence.regimes import classify_regimes, buoyancy_reynolds


def process_downcast(
    dc: Downcast,
    mat,  # MatData
    meta: dict[str, Any],
    dz_bin: float = 0.25,
    dz_eps: float = 2.0,
    nperseg: int = 512,
    exclude_above_dbar: float = 0.0,
    chi_method: str = "batchelor",
    coherence_threshold: float = 0.5,
) -> dict[str, Any]:
    """Run the full processing chain on one Downcast and return a result dict.

    Steps
    -----
    1.  Calibrate FP07 (T1, T2) against JAC-T
    2.  Despike chlorophyll and turbidity
    3.  Compute CT, SA, sigma0 from JAC_T/JAC_C
    4.  Thorpe scales; staircase detection
    5.  Bin slow variables to dz_bin grid; compute N²; compute Turner angle
    6.  Epsilon from sh1 and sh2 (Nasmyth, 5-40 cpm)
    7.  Chi from both FP07s with inter-thermistor coherence rejection; chi_best
    8.  Mixing regime classification (Bouffard & Boegman 2013)
    """
    lat = meta.get("latitude", 0.0)
    lon = meta.get("longitude", 0.0)

    # 1. Calibrate FP07
    T1_cal = calibrate_fp07(dc.T1_fast, dc.t_fast, dc.JAC_T, dc.t_slow)
    T2_cal = calibrate_fp07(dc.T2_fast, dc.t_fast, dc.JAC_T, dc.t_slow)

    # 2. Despike optical sensors
    chl_despiked = despike(dc.Chlorophyll)
    turb_despiked = despike(dc.Turbidity)

    # 3. Oceanographic properties (slow rate)
    CT, SA, sigma0 = compute_ct_sa_density(dc.JAC_T, dc.JAC_C, dc.P_slow, lat, lon)

    # 4. Thorpe scales and staircase detection
    thorpe_disp_slow, thorpe_scale_slow = compute_thorpe_scales(sigma0, dc.P_slow)

    staircase_fast = detect_staircases(T1_cal, dc.P_fast)

    # 5. Bin slow variables; N²; Turner angle
    slow_vars = {
        "CT": CT, "SA": SA, "sigma0": sigma0,
        "thorpe_scale": thorpe_scale_slow, "thorpe_disp": thorpe_disp_slow,
    }
    z_bin, binned_slow = bin_to_grid(slow_vars, dc.P_slow, dz=dz_bin)
    fast_vars = {"chlorophyll": chl_despiked, "turbidity": turb_despiked}
    _, binned_fast = bin_to_grid(fast_vars, dc.P_fast, dz=dz_bin)
    _, binned_staircase = bin_to_grid(
        {"staircase": staircase_fast.astype(float)}, dc.P_fast, dz=dz_bin
    )
    staircase_bin = binned_staircase["staircase"] > 0.5

    N2, p_mid_N2 = compute_N2(SA, CT, dc.P_slow, lat, lon)

    # Turner angle on binned SA/CT
    SA_bin = binned_slow["SA"]
    CT_bin = binned_slow["CT"]
    valid_bin = np.isfinite(SA_bin) & np.isfinite(CT_bin)
    Tu_bin = np.full(len(z_bin), np.nan)
    p_mid_Tu = np.full(len(z_bin) - 1, np.nan)
    if valid_bin.sum() >= 2:
        try:
            Tu_raw, _, p_mid_Tu_raw = compute_turner_angle(
                SA_bin[valid_bin], CT_bin[valid_bin], z_bin[valid_bin], lat
            )
            # Interpolate back onto z_bin centres (Tu is on mid-points)
            if len(p_mid_Tu_raw) > 1:
                f_tu = interp1d(p_mid_Tu_raw, Tu_raw, bounds_error=False, fill_value=np.nan)
                Tu_bin = f_tu(z_bin)
        except Exception:
            pass

    # Depth in metres
    depth_fast_m = -gsw.z_from_p(dc.P_fast, lat)
    depth_slow_m = -gsw.z_from_p(dc.P_slow, lat)

    # 6. Epsilon
    depth_eps, eps1, flag1 = compute_epsilon_profile(
        dc.sh1, dc.P_fast, dc.W_fast, mat.fs_fast,
        accel_flag=dc.accel_flag, dz=dz_eps, nperseg=nperseg,
        exclude_above_dbar=exclude_above_dbar,
    )
    _, eps2, flag2 = compute_epsilon_profile(
        dc.sh2, dc.P_fast, dc.W_fast, mat.fs_fast,
        accel_flag=dc.accel_flag, dz=dz_eps, nperseg=nperseg,
        exclude_above_dbar=exclude_above_dbar,
    )
    eps_best = best_epsilon_estimate(eps1, eps2, method="minimum")
    accel_flag_eps = flag1 | flag2

    # 7. Chi — dual thermistor with coherence rejection
    chi_result = compute_chi_profiles_dual(
        T1_cal, T2_cal, dc.P_fast, dc.W_fast, mat.fs_fast,
        accel_flag=dc.accel_flag, dz=dz_eps, nperseg=nperseg,
        exclude_above_dbar=exclude_above_dbar, method=chi_method,
        coherence_threshold=coherence_threshold,
    )

    # 8. Regime classification: N² and Tu interpolated onto eps depth grid
    N2_on_eps = _interp_to_grid(p_mid_N2, N2, depth_eps)
    Tu_on_eps = _interp_to_grid(z_bin, Tu_bin, depth_eps)
    regime = classify_regimes(eps_best, N2_on_eps, Tu_on_eps)

    return {
        # Fast-rate
        "depth_fast": dc.P_fast,
        "depth_fast_m": depth_fast_m,
        "P_fast": dc.P_fast,
        "W_fast": dc.W_fast,
        "sh1_cal": dc.sh1,
        "sh2_cal": dc.sh2,
        "T1_cal": T1_cal,
        "T2_cal": T2_cal,
        "chlorophyll": chl_despiked,
        "turbidity": turb_despiked,
        "accel_flag": dc.accel_flag.astype(float),
        # Slow-rate
        "depth_slow": dc.P_slow,
        "depth_slow_m": depth_slow_m,
        "JAC_T": dc.JAC_T,
        "JAC_C": dc.JAC_C,
        "CT": CT,
        "SA": SA,
        "sigma0": sigma0,
        # Binned
        "depth_bin": z_bin,
        "CT_bin": CT_bin,
        "SA_bin": SA_bin,
        "sigma0_bin": binned_slow["sigma0"],
        "chlorophyll_bin": binned_fast["chlorophyll"],
        "turbidity_bin": binned_fast["turbidity"],
        "thorpe_scale": binned_slow["thorpe_scale"],
        "thorpe_disp": binned_slow["thorpe_disp"],
        "staircase_flag": staircase_bin.astype(float),
        "Turner_angle": Tu_bin,
        # N²
        "N2": N2,
        "depth_N2": p_mid_N2,
        # Turbulence — epsilon
        "depth_eps": depth_eps,
        "eps1": eps1,
        "eps2": eps2,
        "eps_best": eps_best,
        "eps_accel_flag": accel_flag_eps.astype(float),
        # Turbulence — chi (dual thermistor with coherence rejection)
        "chi1_raw": chi_result["chi1_raw"],
        "chi2_raw": chi_result["chi2_raw"],
        "chi1": chi_result["chi1"],
        "chi2": chi_result["chi2"],
        "chi_best": chi_result["chi_best"],
        "eps_batchelor1": chi_result["eps_batchelor1"],
        "eps_batchelor2": chi_result["eps_batchelor2"],
        "chi_coherence": chi_result["coherence"],
        "chi_flag": chi_result["chi_flag"].astype(float),
        # Regime classification
        "regime": regime,
    }


def _interp_to_grid(
    p_src: np.ndarray,
    v_src: np.ndarray,
    p_tgt: np.ndarray,
) -> np.ndarray:
    """Linear interpolation with NaN fill for out-of-range targets."""
    valid = np.isfinite(p_src) & np.isfinite(v_src)
    if valid.sum() < 2:
        return np.full(len(p_tgt), np.nan)
    f = interp1d(p_src[valid], v_src[valid], bounds_error=False, fill_value=np.nan)
    return f(p_tgt)
