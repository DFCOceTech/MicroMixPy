"""Mixing regime classification (Bouffard & Boegman 2013, REQ-REGIME-001).

Reference
---------
Bouffard, D. & Boegman, L. (2013), A diapycnal diffusivity model for stratified
environmental flows, Dyn. Atmos. Oceans, 61-62, 14-34.
"""

from __future__ import annotations

import numpy as np


# Integer regime codes (REQ-REGIME-002)
INDETERMINATE: int = 0
TURBULENT: int = 1
DOUBLE_DIFFUSION: int = 2
WEAK_MIXING: int = 3

REGIME_NAMES: dict[int, str] = {
    INDETERMINATE: "indeterminate",
    TURBULENT: "turbulent_mixing",
    DOUBLE_DIFFUSION: "double_diffusion",
    WEAK_MIXING: "weak_mixing",
}

_NU: float = 1.0e-6  # kinematic viscosity (m²/s)
_REB_THRESHOLD: float = 20.0   # Bouffard & Boegman (2013)
_TU_THRESHOLD: float = 45.0    # |Turner angle| threshold for double diffusion (degrees)


def buoyancy_reynolds(
    eps: np.ndarray,
    N2: np.ndarray,
    nu: float = _NU,
) -> np.ndarray:
    """Buoyancy Reynolds number Reb = ε / (ν · N²).

    Returns NaN where N² ≤ 0 or either input is NaN.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        Reb = np.where((N2 > 0) & np.isfinite(eps) & np.isfinite(N2),
                       eps / (nu * N2), np.nan)
    return Reb


def classify_regimes(
    eps: np.ndarray,
    N2: np.ndarray,
    Tu: np.ndarray,
    nu: float = _NU,
    reb_threshold: float = _REB_THRESHOLD,
    tu_threshold: float = _TU_THRESHOLD,
) -> np.ndarray:
    """Classify each depth bin into a mixing regime.

    Parameters
    ----------
    eps          : TKE dissipation rate (W/kg) per bin
    N2           : buoyancy frequency squared (s^-2) per bin
    Tu           : Turner angle (degrees) per bin
    nu           : kinematic viscosity (m²/s)
    reb_threshold: Reb threshold for active turbulence (default 20)
    tu_threshold : |Tu| threshold for double diffusion (default 45°)

    Returns
    -------
    regime : integer array of regime codes (INDETERMINATE=0, TURBULENT=1,
             DOUBLE_DIFFUSION=2, WEAK_MIXING=3)
    """
    Reb = buoyancy_reynolds(eps, N2, nu)
    regime = np.full(len(eps), INDETERMINATE, dtype=np.int8)

    valid = np.isfinite(Reb) & np.isfinite(Tu)
    active = valid & (Reb >= reb_threshold)
    dd = valid & (Reb < reb_threshold) & (np.abs(Tu) >= tu_threshold)
    weak = valid & (Reb < reb_threshold) & (np.abs(Tu) < tu_threshold)

    regime[active] = TURBULENT
    regime[dd] = DOUBLE_DIFFUSION
    regime[weak] = WEAK_MIXING

    return regime
