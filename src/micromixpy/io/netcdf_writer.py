"""Write processed VMP profile to netCDF4 with CF-1.8 conventions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr


def write_profile_netcdf(
    output_path: str | Path,
    result: dict[str, Any],
    meta: dict[str, Any],
) -> None:
    """Write a fully-processed profile dict to netCDF4.

    Parameters
    ----------
    output_path : destination .nc file path
    result      : dict with keys matching the variable groups below
    meta        : profile metadata (lat, lon, station_name, date, time, ...)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ds_vars: dict[str, xr.Variable] = {}

    # --- Fast-rate variables ---
    if "depth_fast" in result:
        z_fast = result["depth_fast"]
        ds_vars["depth_fast"] = xr.Variable("z_fast", z_fast, attrs={"units": "dbar", "long_name": "pressure at fast rate"})
        for name, attrs in [
            ("P_fast", {"units": "dbar", "long_name": "pressure"}),
            ("W_fast", {"units": "m s-1", "long_name": "profiler fall speed"}),
            ("sh1_cal", {"units": "s-1", "long_name": "shear probe 1 (calibrated)"}),
            ("sh2_cal", {"units": "s-1", "long_name": "shear probe 2 (calibrated)"}),
            ("T1_cal", {"units": "degC", "long_name": "FP07 thermistor 1 calibrated temperature"}),
            ("T2_cal", {"units": "degC", "long_name": "FP07 thermistor 2 calibrated temperature"}),
            ("chlorophyll", {"units": "ppb", "long_name": "chlorophyll-a fluorescence (despiked)"}),
            ("turbidity", {"units": "FTU", "long_name": "turbidity (despiked)"}),
            ("accel_flag", {"units": "1", "long_name": "acceleration region flag (1=contaminated)"}),
            ("depth_fast_m", {"units": "m", "long_name": "depth in metres (positive downward)"}),
        ]:
            if name in result:
                ds_vars[name] = xr.Variable("z_fast", result[name], attrs=attrs)

    # --- Slow-rate (JAC) variables ---
    if "depth_slow" in result:
        ds_vars["depth_slow"] = xr.Variable("z_slow", result["depth_slow"], attrs={"units": "dbar", "long_name": "pressure at slow (JAC) rate"})
        for name, attrs in [
            ("depth_slow_m", {"units": "m", "long_name": "depth in metres (positive downward)"}),
            ("JAC_T", {"units": "degC", "long_name": "JAC temperature"}),
            ("JAC_C", {"units": "mS cm-1", "long_name": "JAC conductivity"}),
            ("CT", {"units": "degC", "long_name": "Conservative Temperature (TEOS-10)"}),
            ("SA", {"units": "g kg-1", "long_name": "Absolute Salinity (TEOS-10)"}),
            ("sigma0", {"units": "kg m-3", "long_name": "potential density anomaly referenced to 0 dbar"}),
        ]:
            if name in result:
                ds_vars[name] = xr.Variable("z_slow", result[name], attrs=attrs)

    # --- Binned (0.25 m) variables ---
    if "depth_bin" in result:
        ds_vars["depth_bin"] = xr.Variable("z_bin", result["depth_bin"], attrs={"units": "dbar", "long_name": "bin-center pressure (0.25 dbar bins)"})
        for name, attrs in [
            ("CT_bin", {"units": "degC", "long_name": "binned Conservative Temperature"}),
            ("SA_bin", {"units": "g kg-1", "long_name": "binned Absolute Salinity"}),
            ("sigma0_bin", {"units": "kg m-3", "long_name": "binned potential density anomaly"}),
            ("chlorophyll_bin", {"units": "ppb", "long_name": "binned despiked chlorophyll-a"}),
            ("turbidity_bin", {"units": "FTU", "long_name": "binned despiked turbidity"}),
            ("thorpe_scale", {"units": "m", "long_name": "Thorpe scale"}),
            ("thorpe_disp", {"units": "m", "long_name": "Thorpe displacement"}),
            ("staircase_flag", {"units": "1", "long_name": "thermohaline staircase flag"}),
            ("Turner_angle", {"units": "degrees", "long_name": "Turner angle (positive=salt fingering)"}),
        ]:
            if name in result:
                ds_vars[name] = xr.Variable("z_bin", result[name], attrs=attrs)

    # --- N² on mid-pressure grid ---
    if "N2" in result:
        ds_vars["N2"] = xr.Variable("z_N2", result["N2"], attrs={"units": "s-2", "long_name": "buoyancy frequency squared"})
        if "depth_N2" in result:
            ds_vars["depth_N2"] = xr.Variable("z_N2", result["depth_N2"], attrs={"units": "dbar"})

    # --- Turbulence profiles ---
    if "depth_eps" in result:
        ds_vars["depth_eps"] = xr.Variable("z_eps", result["depth_eps"], attrs={"units": "dbar", "long_name": "bin-center pressure for turbulence estimates"})
        for name, attrs in [
            ("eps1", {"units": "W kg-1", "long_name": "epsilon from shear probe 1 (Nasmyth fit)"}),
            ("eps2", {"units": "W kg-1", "long_name": "epsilon from shear probe 2 (Nasmyth fit)"}),
            ("eps_best", {"units": "W kg-1", "long_name": "best-estimate epsilon (minimum of eps1, eps2)"}),
            ("chi1_raw", {"units": "K2 s-1", "long_name": "chi T1 before coherence masking"}),
            ("chi2_raw", {"units": "K2 s-1", "long_name": "chi T2 before coherence masking"}),
            ("chi1", {"units": "K2 s-1", "long_name": "chi from FP07 thermistor 1 (coherence-masked)"}),
            ("chi2", {"units": "K2 s-1", "long_name": "chi from FP07 thermistor 2 (coherence-masked)"}),
            ("chi_best", {"units": "K2 s-1", "long_name": "best-estimate chi (log-mean of passing probes)"}),
            ("eps_batchelor1", {"units": "W kg-1", "long_name": "epsilon from Batchelor fit of T1 gradient spectrum"}),
            ("eps_batchelor2", {"units": "W kg-1", "long_name": "epsilon from Batchelor fit of T2 gradient spectrum"}),
            ("chi_coherence", {"units": "1", "long_name": "inter-thermistor spectral coherence (0-1)"}),
            ("chi_flag", {"units": "1", "long_name": "chi coherence quality flag (1=low coherence, rejected)"}),
            ("regime", {"units": "1", "long_name": "mixing regime (0=indeterminate,1=turbulent,2=double_diffusion,3=weak)",
                        "flag_values": "0 1 2 3",
                        "flag_meanings": "indeterminate turbulent_mixing double_diffusion weak_mixing"}),
            ("eps_accel_flag", {"units": "1", "long_name": "epsilon bin contaminated by acceleration"}),
        ]:
            if name in result:
                ds_vars[name] = xr.Variable("z_eps", result[name], attrs=attrs)

    ds = xr.Dataset(ds_vars)

    # Global attributes
    station = meta.get("station_name", "unknown")
    file_name = meta.get("file_name", "unknown")
    profile_num = meta.get("profile_number", 0)
    ds.attrs.update(
        {
            "Conventions": "CF-1.8",
            "title": f"VMP-250 turbulent mixing profile — {station}",
            "institution": "University of Manitoba / LAKO Cruise",
            "source": f"{file_name}.mat profile {profile_num}",
            "history": "Processed by MicroMixPy",
            "station_name": station,
            "date": meta.get("date", ""),
            "time": meta.get("time", ""),
            "latitude": meta.get("latitude", np.nan),
            "longitude": meta.get("longitude", np.nan),
            "profile_number": profile_num,
            "file_name": file_name,
        }
    )

    nc_path = str(output_path)
    if not nc_path.endswith(".nc"):
        nc_path += ".nc"
    ds.to_netcdf(nc_path, format="NETCDF4")
