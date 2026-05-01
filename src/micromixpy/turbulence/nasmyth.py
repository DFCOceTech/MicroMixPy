"""Nasmyth universal shear spectrum and epsilon fitting."""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar


_NU_DEFAULT = 1.0e-6  # kinematic viscosity of seawater (m²/s)

# Standard fitting band for the inertial subrange (Oakey 1982; Lueck et al. 2002).
# Below 5 cpm: contaminated by ship/mooring motion and low-frequency shear.
# Above 40 cpm: approaches the viscous subrange at typical ocean epsilon values;
#               VMP vibration peaks often appear here.
K_FIT_MIN: float = 5.0   # cpm
K_FIT_MAX: float = 40.0  # cpm


def nasmyth_spectrum(k: np.ndarray, epsilon: float, nu: float = _NU_DEFAULT) -> np.ndarray:
    """Nasmyth (1970) universal shear variance spectrum.

    phi_N(k) = (eps^3 * nu)^(1/4) * 8.05 * x^(1/3) / (1 + (20.6*x)^3.715)

    where x = k * eta and eta = (nu^3 / eps)^(1/4) is the Kolmogorov microscale.

    Parameters
    ----------
    k       : wavenumber array (cycles per metre, cpm)
    epsilon : dissipation rate (W/kg)
    nu      : kinematic viscosity (m²/s)

    Returns
    -------
    phi : shear spectrum (s^-2 / cpm)
    """
    eta = (nu**3 / epsilon) ** 0.25
    x = k * eta
    phi = (epsilon**3 * nu) ** 0.25 * 8.05 * x ** (1.0 / 3.0) / (1.0 + (20.6 * x) ** 3.715)
    return phi


def fit_epsilon(
    k: np.ndarray,
    phi_obs: np.ndarray,
    nu: float = _NU_DEFAULT,
    k_min: float = K_FIT_MIN,
    k_max: float = K_FIT_MAX,
) -> float:
    """Fit the Nasmyth spectrum to observed shear PSD over a fixed wavenumber band.

    Minimises log-space RMS misfit over the fixed inertial-subrange band
    [k_min, k_max] = [5, 40] cpm by default.  The fixed band avoids low-frequency
    contamination and the viscous roll-off at high wavenumber.

    Parameters
    ----------
    k       : wavenumber array (cpm), same length as phi_obs
    phi_obs : observed shear PSD (s^-2 / cpm)
    nu      : kinematic viscosity (m²/s)
    k_min   : lower fitting bound (cpm); default 5
    k_max   : upper fitting bound (cpm); default 40

    Returns
    -------
    epsilon : estimated dissipation rate (W/kg); NaN if fewer than 3 bins in band
    """
    fit_mask = (k >= k_min) & (k <= k_max) & np.isfinite(phi_obs) & (phi_obs > 0)
    if fit_mask.sum() < 3:
        return np.nan

    k_fit = k[fit_mask]
    phi_fit = phi_obs[fit_mask]
    log_phi = np.log10(phi_fit)

    def _misfit(log_eps: float) -> float:
        eps_try = 10.0**log_eps
        phi_model = nasmyth_spectrum(k_fit, eps_try, nu)
        phi_model = np.where(phi_model > 0, phi_model, 1e-30)
        return float(np.mean((log_phi - np.log10(phi_model)) ** 2))

    result = minimize_scalar(_misfit, bounds=(-14.0, -2.0), method="bounded")
    return float(10.0 ** result.x)
