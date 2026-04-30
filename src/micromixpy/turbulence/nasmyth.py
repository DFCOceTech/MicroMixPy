"""Nasmyth universal shear spectrum and iterative epsilon fitting."""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar


_NU_DEFAULT = 1.0e-6  # kinematic viscosity of seawater (m²/s)


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


def _kolmogorov_wavenumber(epsilon: float, nu: float = _NU_DEFAULT) -> float:
    """Kolmogorov wavenumber k_eta = 1 / (2π * eta) [cpm]."""
    eta = (nu**3 / epsilon) ** 0.25
    return 1.0 / (2.0 * np.pi * eta)


def fit_epsilon(
    k: np.ndarray,
    phi_obs: np.ndarray,
    nu: float = _NU_DEFAULT,
    k_min: float = 1.0,
    k_max_frac: float = 0.5,
    max_iter: int = 5,
) -> float:
    """Iterative least-squares fit of Nasmyth spectrum to observed shear PSD.

    Parameters
    ----------
    k          : wavenumber array (cpm), same length as phi_obs
    phi_obs    : observed shear spectrum (s^-2 / cpm)
    nu         : kinematic viscosity (m²/s)
    k_min      : lower wavenumber bound for fitting (cpm)
    k_max_frac : upper bound = k_max_frac * k_eta (Kolmogorov wavenumber);
                 clamped to Nyquist to avoid fitting into noise floor
    max_iter   : number of iterations to refine k_max

    Returns
    -------
    epsilon : estimated dissipation rate (W/kg); NaN if fit fails
    """
    k_nyquist = float(k[-1]) if len(k) > 0 else 1.0

    # Initial estimate: integrate only the low-k portion (first 20% of range)
    # to avoid noise-floor contamination at high wavenumbers.
    k_init_max = min(k_nyquist, max(k_min * 10, 30.0))
    valid_init = (k >= k_min) & (k <= k_init_max) & np.isfinite(phi_obs) & (phi_obs > 0)
    if valid_init.sum() < 3:
        # Broaden to full valid range if low-k range has too few bins
        valid_init = (k >= k_min) & np.isfinite(phi_obs) & (phi_obs > 0)
    if valid_init.sum() < 3:
        return np.nan

    eps_init = 7.5 * nu * float(np.trapezoid(phi_obs[valid_init], k[valid_init]))
    eps_init = max(eps_init, 1e-12)
    eps = eps_init

    for _ in range(max_iter):
        k_eta = _kolmogorov_wavenumber(eps, nu)
        # Clamp to Nyquist so we never try to fit into the noise floor
        k_upper = min(k_max_frac * k_eta, k_nyquist * 0.9)
        k_upper = max(k_upper, k_min * 2)

        fit_mask = (k >= k_min) & (k <= k_upper) & np.isfinite(phi_obs) & (phi_obs > 0)
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

        result = minimize_scalar(
            _misfit,
            bounds=(-14.0, -2.0),
            method="bounded",
        )
        eps = 10.0 ** result.x

    return float(eps)
