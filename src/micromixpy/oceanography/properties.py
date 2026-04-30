"""Compute oceanographic state variables using TEOS-10 (gsw)."""

from __future__ import annotations

import gsw
import numpy as np


def compute_ct_sa_density(
    JAC_T: np.ndarray,
    JAC_C: np.ndarray,
    pressure: np.ndarray,
    latitude: float = 0.0,
    longitude: float = 0.0,
    *,
    lat: float | None = None,
    lon: float | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute Conservative Temperature, Absolute Salinity, and potential density.

    Parameters
    ----------
    JAC_T    : in-situ temperature from JAC-T (°C) at slow rate
    JAC_C    : conductivity from JAC-C (mS/cm) at slow rate
    pressure : pressure (dbar) at slow rate
    latitude : decimal degrees N
    longitude: decimal degrees E

    Returns
    -------
    CT    : Conservative Temperature (°C)
    SA    : Absolute Salinity (g/kg)
    sigma0: potential density anomaly referenced to 0 dbar (kg/m³)
    """
    # lat/lon keyword aliases for convenience
    if lat is not None:
        latitude = lat
    if lon is not None:
        longitude = lon
    # gsw expects conductivity in mS/cm; JAC_C is already in mS/cm
    SP = gsw.SP_from_C(JAC_C, JAC_T, pressure)
    SA = gsw.SA_from_SP(SP, pressure, longitude, latitude)
    CT = gsw.CT_from_t(SA, JAC_T, pressure)
    sigma0 = gsw.sigma0(SA, CT)
    return CT, SA, sigma0


def compute_N2(
    SA: np.ndarray,
    CT: np.ndarray,
    pressure: np.ndarray,
    latitude: float,
    longitude: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute buoyancy frequency squared N² using gsw.Nsquared.

    Returns N2 and the mid-pressure array (one element shorter than input).
    """
    N2, p_mid = gsw.Nsquared(SA, CT, pressure, lat=latitude)
    return N2, p_mid
