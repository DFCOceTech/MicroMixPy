"""Turner angle and density ratio from binned CTD data (REQ-TURNER-001)."""

from __future__ import annotations

import gsw
import numpy as np


def compute_turner_angle(
    SA: np.ndarray,
    CT: np.ndarray,
    pressure: np.ndarray,
    lat: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute Turner angle and density ratio from Absolute Salinity and
    Conservative Temperature profiles using gsw.Turner_Rsubrho.

    The Turner angle encodes the relative contributions of temperature and salinity
    to vertical density stratification:
      Tu >  45°: salt-fingering regime (T stabilising, S destabilising)
      Tu < -45°: diffusive-layering regime
      |Tu| < 45°: doubly stable or shear-dominated

    Parameters
    ----------
    SA       : Absolute Salinity (g/kg) at binned depths
    CT       : Conservative Temperature (°C) at binned depths
    pressure : pressure (dbar) at binned depths
    lat      : latitude (degrees N)

    Returns
    -------
    Tu    : Turner angle (degrees) at mid-bin depths — length n-1
    Rr    : Density ratio R_rho at mid-bin depths
    p_mid : mid-bin pressure (dbar)
    """
    # gsw.Turner_Rsubrho already returns Tu in degrees (not radians)
    Tu_deg, Rr, p_mid = gsw.Turner_Rsubrho(SA, CT, pressure)
    return Tu_deg, Rr, p_mid
