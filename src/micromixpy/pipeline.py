"""End-to-end processing pipeline for a single VMP downcast."""

from __future__ import annotations

from typing import Any

import numpy as np

import gsw

from .processing.calibration import calibrate_fp07
from .processing.downcasts import Downcast
from .processing.optics import despike
from .oceanography.properties import compute_ct_sa_density, compute_N2
from .oceanography.thorpe import compute_thorpe_scales, detect_staircases
from .oceanography.binning import bin_to_grid
from .turbulence.dissipation import (
    compute_epsilon_profile,
    compute_chi_profile,
    best_epsilon_estimate,
)


def process_downcast(
    dc: Downcast,
    mat,  # MatData
    meta: dict[str, Any],
    dz_bin: float = 0.25,
    dz_eps: float = 2.0,
    nperseg: int = 512,
    exclude_above_dbar: float = 0.0,
) -> dict[str, Any]:
    """Run the full processing chain on one Downcast and return a result dict.

    Steps
    -----
    1. Calibrate FP07 (T1, T2) against JAC-T
    2. Despike chlorophyll and turbidity
    3. Compute CT, SA, sigma0 from JAC_T/JAC_C
    4. Compute Thorpe scales and staircase flag
    5. Bin slow variables to dz_bin grid; compute N²
    6. Compute epsilon from sh1 and sh2 (Nasmyth fit); sh1/sh2 already in s^-1
    7. Compute chi from calibrated T1 and T2
    8. Combine into best-estimate epsilon
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

    # 4. Thorpe scales (slow rate)
    thorpe_disp_slow, thorpe_scale_slow = compute_thorpe_scales(sigma0, dc.P_slow)

    # 5. Bin slow variables to dz_bin grid
    slow_vars = {"CT": CT, "SA": SA, "sigma0": sigma0, "thorpe_scale": thorpe_scale_slow, "thorpe_disp": thorpe_disp_slow}
    z_bin, binned_slow = bin_to_grid(slow_vars, dc.P_slow, dz=dz_bin)

    fast_vars = {"chlorophyll": chl_despiked, "turbidity": turb_despiked}
    _, binned_fast = bin_to_grid(fast_vars, dc.P_fast, dz=dz_bin)

    N2, p_mid = compute_N2(SA, CT, dc.P_slow, lat, lon)

    # Staircase detection (fast rate, calibrated T1)
    staircase_fast = detect_staircases(T1_cal, dc.P_fast)
    _, binned_staircase = bin_to_grid({"staircase": staircase_fast.astype(float)}, dc.P_fast, dz=dz_bin)
    staircase_bin = binned_staircase["staircase"] > 0.5

    # Depth in metres (negative convention) from pressure for all grids
    depth_fast_m = -gsw.z_from_p(dc.P_fast, lat)   # positive downward
    depth_slow_m = -gsw.z_from_p(dc.P_slow, lat)

    # 6. Epsilon — sh1/sh2 are already in s^-1 (calibrated by ODAS quicklook)
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

    # 7. Chi from calibrated FP07 temperatures
    _, chi1 = compute_chi_profile(T1_cal, dc.P_fast, dc.W_fast, mat.fs_fast,
        accel_flag=dc.accel_flag, dz=dz_eps, nperseg=nperseg,
        exclude_above_dbar=exclude_above_dbar)
    _, chi2 = compute_chi_profile(T2_cal, dc.P_fast, dc.W_fast, mat.fs_fast,
        accel_flag=dc.accel_flag, dz=dz_eps, nperseg=nperseg,
        exclude_above_dbar=exclude_above_dbar)

    # 8. Best estimate epsilon
    eps_best = best_epsilon_estimate(eps1, eps2, method="minimum")
    accel_flag_eps = flag1 | flag2

    return {
        # Fast-rate
        "depth_fast": dc.P_fast,   # pressure (dbar) — used as vertical coordinate
        "depth_fast_m": depth_fast_m,  # depth in metres (positive downward)
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
        "CT_bin": binned_slow["CT"],
        "SA_bin": binned_slow["SA"],
        "sigma0_bin": binned_slow["sigma0"],
        "chlorophyll_bin": binned_fast["chlorophyll"],
        "turbidity_bin": binned_fast["turbidity"],
        "thorpe_scale": binned_slow["thorpe_scale"],
        "thorpe_disp": binned_slow["thorpe_disp"],
        "staircase_flag": staircase_bin.astype(float),
        # N²
        "N2": N2,
        "depth_N2": p_mid,
        # Turbulence
        "depth_eps": depth_eps,
        "eps1": eps1,
        "eps2": eps2,
        "eps_best": eps_best,
        "chi1": chi1,
        "chi2": chi2,
        "eps_accel_flag": accel_flag_eps.astype(float),
    }
