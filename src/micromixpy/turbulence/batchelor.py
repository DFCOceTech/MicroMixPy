"""Batchelor (1959) temperature gradient spectrum and chi/epsilon fitting.

Reference
---------
Batchelor, G. K. (1959), Small-scale variation of convected quantities like
temperature in a turbulent fluid, J. Fluid Mech., 5, 113-133.

Spectral shape constant q = 3.7 from:
Oakey, N. S. (1982), Determination of the rate of dissipation of turbulent
energy from simultaneous temperature and velocity shear microstructure
measurements, J. Phys. Oceanogr., 12, 256-271.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


_Q: float = 3.7        # Oakey (1982) spectral shape constant

# Standard wavenumber band for Batchelor fitting (same rationale as Nasmyth 5-40 cpm,
# but extended upward since temperature diffuses at smaller scales than velocity).
K_BATCHELOR_MIN: float = 5.0    # cpm — lower bound (avoid low-freq contamination)
K_BATCHELOR_MAX: float = 100.0  # cpm — upper bound (well into viscous-diffusive range)
_NU: float = 1.0e-6    # kinematic viscosity (m²/s)
_KAPPA_T: float = 1.4e-7  # thermal diffusivity (m²/s)


def batchelor_wavenumber(
    eps: float,
    nu: float = _NU,
    kappa_T: float = _KAPPA_T,
) -> float:
    """Batchelor wavenumber k_B = (ε / (ν κ_T²))^(1/4) / (2π)  [cycles/m].

    The Batchelor spectrum rolls off near k_B; the spectral peak is at
    k_B / sqrt(2*q) ≈ 0.37 * k_B.
    """
    return (eps / (nu * kappa_T**2)) ** 0.25 / (2.0 * np.pi)


def batchelor_spectrum(
    k: np.ndarray,
    chi: float,
    eps: float,
    nu: float = _NU,
    kappa_T: float = _KAPPA_T,
) -> np.ndarray:
    """Batchelor (1959) temperature gradient PSD.

    Φ_B(k) = chi / (6 · κ_T · k_B) · 2q · (k/k_B) · exp(−q · (k/k_B)²)

    This formulation is normalised so that:
        chi = 6 · κ_T · ∫₀^∞ Φ_B(k) dk

    consistent with the direct-integration definition chi = 6·κ_T·<(dT/dz)²>.

    Parameters
    ----------
    k       : wavenumber array (cpm = cycles/m)
    chi     : temperature variance dissipation rate (K²/s)
    eps     : TKE dissipation rate (W/kg) — sets k_B
    nu      : kinematic viscosity (m²/s)
    kappa_T : thermal diffusivity (m²/s)

    Returns
    -------
    phi : Batchelor temperature-gradient PSD (K² m = (K/m)² / (m⁻¹))
          Same units as the output of `temperature_gradient_psd`.
    """
    k_B = batchelor_wavenumber(eps, nu, kappa_T)
    u = k / k_B
    G = 2.0 * _Q * u * np.exp(-_Q * u**2)   # ∫₀^∞ G(u) du = 1
    return chi / (6.0 * kappa_T * k_B) * G


def fit_batchelor(
    k: np.ndarray,
    phi_obs: np.ndarray,
    k_nyquist: float,
    nu: float = _NU,
    kappa_T: float = _KAPPA_T,
    nyquist_frac: float = 0.5,
) -> tuple[float, float]:
    """Fit the Batchelor spectrum to an observed temperature gradient PSD.

    Minimises the log-space RMS misfit over (chi, eps) simultaneously.
    The spectral shape encodes both the amplitude (chi) and the rolloff
    wavenumber (k_B → eps), providing an independent estimate of epsilon.

    Parameters
    ----------
    k           : wavenumber array (cpm), same length as phi_obs
    phi_obs     : observed temperature gradient PSD (K² m⁻¹)
    k_nyquist   : Nyquist wavenumber of the segment (cpm)
    nu          : kinematic viscosity (m²/s)
    kappa_T     : thermal diffusivity (m²/s)
    nyquist_frac: if fitted k_B > nyquist_frac * k_nyquist, eps is returned
                  as NaN (spectral rolloff not resolved). Default 0.5.

    Returns
    -------
    chi         : fitted temperature variance dissipation rate (K²/s), or NaN
    eps_batchelor : TKE dissipation from k_B (W/kg), or NaN if k_B near Nyquist
    """
    valid = np.isfinite(phi_obs) & (phi_obs > 0) & np.isfinite(k) & (k > 0)
    if valid.sum() < 5:
        return np.nan, np.nan

    k_v = k[valid]
    log_phi = np.log10(phi_obs[valid])

    # Initial guess for chi via direct integration over the observed range
    chi_0 = 6.0 * kappa_T * float(np.trapezoid(phi_obs[valid], k_v))
    chi_0 = max(chi_0, 1e-14)

    # Initial guess for eps: use the wavenumber of peak observed PSD
    # k_peak ≈ k_B / sqrt(2*q) → k_B_0 ≈ k_peak * sqrt(2*q)
    k_peak = float(k_v[np.argmax(phi_obs[valid])])
    k_B_0 = k_peak * np.sqrt(2.0 * _Q)
    # Clamp k_B_0 away from boundaries
    k_B_0 = np.clip(k_B_0, 1.0, k_nyquist * 2)
    eps_0 = (k_B_0 * 2.0 * np.pi) ** 4 * nu * kappa_T**2
    eps_0 = max(eps_0, 1e-14)

    def _misfit(params: np.ndarray) -> float:
        log_chi, log_eps = params
        chi_try = 10.0**log_chi
        eps_try = 10.0**log_eps
        phi_model = batchelor_spectrum(k_v, chi_try, eps_try, nu, kappa_T)
        phi_model = np.where(phi_model > 0, phi_model, 1e-30)
        return float(np.mean((log_phi - np.log10(phi_model)) ** 2))

    x0 = np.array([np.log10(chi_0), np.log10(eps_0)])
    bounds = [(-16.0, -2.0), (-14.0, -2.0)]  # log10 bounds for chi and eps

    result = minimize(
        _misfit,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 200, "ftol": 1e-12},
    )

    if not result.success and result.fun > 2.0:
        # Retry from a grid of starting points if first attempt failed badly
        best = result
        for log_eps_try in np.linspace(-12.0, -4.0, 5):
            x_try = np.array([x0[0], log_eps_try])
            r = minimize(_misfit, x_try, method="L-BFGS-B", bounds=bounds,
                         options={"maxiter": 200, "ftol": 1e-12})
            if r.fun < best.fun:
                best = r
        result = best

    chi_fit = 10.0 ** result.x[0]
    eps_fit = 10.0 ** result.x[1]

    # REQ-TDISS-006: if fitted k_B exceeds the reliable detection limit, the spectrum
    # rolloff is not resolved.  Both eps and chi are unreliable in that regime because
    # the fit is constrained only by the rising slope (no rolloff information).
    k_B_fit = batchelor_wavenumber(eps_fit, nu, kappa_T)
    if k_B_fit > nyquist_frac * k_nyquist:
        eps_fit = np.nan
        chi_fit = np.nan  # chi from rising-slope-only fit has no reliable normalization

    return float(chi_fit), float(eps_fit)
