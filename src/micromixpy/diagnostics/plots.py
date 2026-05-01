"""Diagnostic plots for processed VMP profiles (REQ-PLOT-001 through REQ-PLOT-009).

All functions accept an xarray Dataset (from a processed netCDF) and return
a matplotlib Figure.  plot_all() saves every figure to a directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for file output
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import xarray as xr

from ..turbulence.regimes import TURBULENT, DOUBLE_DIFFUSION, WEAK_MIXING, INDETERMINATE, REGIME_NAMES

# Latent heat and heat capacity for Gade line
_L_ICE: float = 334_000.0   # J/kg
_C_PW: float = 3_985.0      # J/(kg·K)

# Regime colours
_REGIME_COLORS = {
    TURBULENT: "#e6194b",        # red
    DOUBLE_DIFFUSION: "#4363d8", # blue
    WEAK_MIXING: "#808000",      # olive
    INDETERMINATE: "#aaaaaa",    # grey
}
_REGIME_LABELS = {k: REGIME_NAMES[k].replace("_", " ") for k in REGIME_NAMES}


# ─── helpers ───────────────────────────────────────────────────────────────────

def _depth_axis(ax: plt.Axes, label: str = "Pressure (dbar)") -> None:
    ax.invert_yaxis()
    ax.set_ylabel(label)


def _gade_line(
    T_AW: float, S_AW: float, T_ice: float = -2.0,
    S_min: float | None = None, S_max: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute the Gade (1979) glacial meltwater mixing line in T-S space.

    T_FW = T_ice − L_ice / c_pw  (effective freshwater temperature)
    T(S) = T_FW + (T_AW − T_FW) · S / S_AW

    S_min/S_max clip the line to the visible data range.
    """
    T_FW = T_ice - _L_ICE / _C_PW
    lo = S_min if S_min is not None else 0.0
    hi = S_max if S_max is not None else S_AW
    S_range = np.linspace(lo, hi, 200)
    T_range = T_FW + (T_AW - T_FW) * S_range / S_AW
    return S_range, T_range


def _ts_bounds(SA: np.ndarray, CT: np.ndarray, pad: float = 0.05) -> tuple[float, float, float, float]:
    """Return (S_lo, S_hi, T_lo, T_hi) padded by *pad* fraction of range."""
    S_lo, S_hi = float(np.nanmin(SA)), float(np.nanmax(SA))
    T_lo, T_hi = float(np.nanmin(CT)), float(np.nanmax(CT))
    S_pad = max((S_hi - S_lo) * pad, 1e-3)
    T_pad = max((T_hi - T_lo) * pad, 1e-3)
    return S_lo - S_pad, S_hi + S_pad, T_lo - T_pad, T_hi + T_pad


# ─── individual plot functions ─────────────────────────────────────────────────

def plot_ts(ds: xr.Dataset) -> plt.Figure:
    """REQ-PLOT-002: simple T-S diagram from binned CTD data."""
    fig, ax = plt.subplots(figsize=(5, 5))
    SA = ds["SA_bin"].values if "SA_bin" in ds else ds["SA"].values
    CT = ds["CT_bin"].values if "CT_bin" in ds else ds["CT"].values
    ax.plot(SA, CT, "k.", ms=3, alpha=0.6)
    ax.set_xlabel("Absolute Salinity (g/kg)")
    ax.set_ylabel("Conservative Temperature (°C)")
    ax.set_title(f"T-S diagram — {ds.attrs.get('station_name', '')}")
    fig.tight_layout()
    return fig


def plot_ts_gade(
    ds: xr.Dataset,
    T_AW: float | None = None,
    S_AW: float | None = None,
    T_ice: float = -2.0,
) -> plt.Figure:
    """REQ-PLOT-003: T-S diagram with Gade glacial meltwater mixing line.

    Parameters default to the warmest/saltiest point in the profile.
    """
    SA = ds["SA_bin"].values if "SA_bin" in ds else ds["SA"].values
    CT = ds["CT_bin"].values if "CT_bin" in ds else ds["CT"].values

    if S_AW is None:
        S_AW = float(np.nanmax(SA))
    if T_AW is None:
        T_AW = float(CT[np.nanargmax(SA)])

    S_lo, S_hi, T_lo, T_hi = _ts_bounds(SA, CT)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(SA, CT, "k.", ms=3, alpha=0.6, label="Profile")
    S_g, T_g = _gade_line(T_AW, S_AW, T_ice, S_min=S_lo, S_max=S_hi)
    ax.plot(S_g, T_g, "b--", lw=1.5, label=f"Gade line (T_ice={T_ice}°C)")
    ax.plot(S_AW, T_AW, "r*", ms=10, label=f"AW end-member ({T_AW:.1f}°C, {S_AW:.1f} g/kg)")
    ax.set_xlim(S_lo, S_hi)
    ax.set_ylim(T_lo, T_hi)
    ax.set_xlabel("Absolute Salinity (g/kg)")
    ax.set_ylabel("Conservative Temperature (°C)")
    ax.set_title(f"T-S + Gade line — {ds.attrs.get('station_name', '')}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def plot_ts_scalar(
    ds: xr.Dataset,
    scalar_var: str = "turbidity_bin",
    cmap: str = "viridis",
    log_scale: bool = False,
    T_AW: float | None = None,
    S_AW: float | None = None,
    T_ice: float = -2.0,
) -> plt.Figure:
    """REQ-PLOT-004: T-S scatter coloured by a scalar variable with Gade overlay."""
    SA = ds["SA_bin"].values if "SA_bin" in ds else ds["SA"].values
    CT = ds["CT_bin"].values if "CT_bin" in ds else ds["CT"].values
    scalar = ds[scalar_var].values if scalar_var in ds else np.full(len(SA), np.nan)

    if S_AW is None:
        S_AW = float(np.nanmax(SA))
    if T_AW is None:
        T_AW = float(CT[np.nanargmax(SA)])

    S_lo, S_hi, T_lo, T_hi = _ts_bounds(SA, CT)
    c_vals = scalar.copy().astype(float)
    pos = c_vals[np.isfinite(c_vals) & (c_vals > 0)]
    norm = mcolors.LogNorm(vmin=pos.min(), vmax=pos.max()) if log_scale and len(pos) else None

    fig, ax = plt.subplots(figsize=(5.5, 5))
    sc = ax.scatter(SA, CT, c=c_vals, cmap=cmap, s=10, norm=norm, zorder=3)
    S_g, T_g = _gade_line(T_AW, S_AW, T_ice, S_min=S_lo, S_max=S_hi)
    ax.plot(S_g, T_g, "k--", lw=1, alpha=0.6, label="Gade line")
    ax.set_xlim(S_lo, S_hi)
    ax.set_ylim(T_lo, T_hi)
    plt.colorbar(sc, ax=ax, label=scalar_var.replace("_", " "))
    ax.set_xlabel("Absolute Salinity (g/kg)")
    ax.set_ylabel("Conservative Temperature (°C)")
    ax.set_title(f"T-S coloured by {scalar_var} — {ds.attrs.get('station_name', '')}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def plot_epsilon_profiles(ds: xr.Dataset) -> plt.Figure:
    """REQ-PLOT-005: vertical epsilon profiles on log x-axis."""
    fig, ax = plt.subplots(figsize=(5, 7))
    d = ds["depth_eps"].values

    for var, label, color, ls in [
        ("eps1",    "ε₁ (sh1)",     "#e6194b", "--"),
        ("eps2",    "ε₂ (sh2)",     "#4363d8", ":"),
        ("eps_best","ε best (min)", "k",       "-"),
    ]:
        if var in ds:
            v = ds[var].values
            valid = np.isfinite(v) & (v > 0)
            if valid.any():
                ax.semilogx(v[valid], d[valid], color=color, ls=ls,
                            lw=1.5, marker="o", ms=3, label=label)

    _depth_axis(ax)
    ax.set_xlabel("ε (W/kg)")
    ax.set_title(f"Epsilon profiles — {ds.attrs.get('station_name', '')}")
    ax.legend(fontsize=9)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_chi_profiles(ds: xr.Dataset) -> plt.Figure:
    """REQ-PLOT-006: vertical chi profiles on log x-axis."""
    fig, ax = plt.subplots(figsize=(5, 7))
    d = ds["depth_eps"].values

    for var, label, color, ls in [
        ("chi1",    "χ₁ (T1)",      "#e6194b", "--"),
        ("chi2",    "χ₂ (T2)",      "#4363d8", ":"),
        ("chi_best","χ best",       "k",       "-"),
    ]:
        if var in ds:
            v = ds[var].values
            valid = np.isfinite(v) & (v > 0)
            if valid.any():
                ax.semilogx(v[valid], d[valid], color=color, ls=ls,
                            lw=1.5, marker="o", ms=3, label=label)

    _depth_axis(ax)
    ax.set_xlabel("χ (K²/s)")
    ax.set_title(f"Chi profiles — {ds.attrs.get('station_name', '')}")
    ax.legend(fontsize=9)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_chi_epsilon_diagram(ds: xr.Dataset) -> plt.Figure:
    """REQ-PLOT-007: chi-epsilon scatter with Bouffard & Boegman (2013) regimes."""
    fig, ax = plt.subplots(figsize=(6, 6))

    eps = ds["eps_best"].values if "eps_best" in ds else None
    chi = ds["chi_best"].values if "chi_best" in ds else (
          ds["chi1"].values if "chi1" in ds else None)
    regime = ds["regime"].values if "regime" in ds else None

    if eps is None or chi is None:
        ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center")
        return fig

    # Shade regime regions: background lines
    _add_regime_shading(ax)

    # Scatter coloured by regime
    for reg_code, color in _REGIME_COLORS.items():
        mask = (regime == reg_code) if regime is not None else np.ones(len(eps), dtype=bool)
        v = np.isfinite(eps) & np.isfinite(chi) & (eps > 0) & (chi > 0) & mask
        if v.any():
            ax.loglog(eps[v], chi[v], ".", color=color, ms=7,
                      label=_REGIME_LABELS[reg_code], alpha=0.8)

    ax.set_xlabel("ε (W/kg)")
    ax.set_ylabel("χ (K²/s)")
    ax.set_title(f"χ–ε diagram — {ds.attrs.get('station_name', '')}")
    ax.legend(fontsize=9)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    return fig


def _add_regime_shading(ax: plt.Axes) -> None:
    """Add Bouffard & Boegman (2013) regime reference lines to a log-log chi-eps plot."""
    # Constant Reb = epsilon / (nu * N²) lines require N², so we just draw
    # a reference line Reb = 20 for a representative N² = 1e-4 s^-2
    nu = 1e-6
    N2_ref = 1e-4
    eps_line = np.logspace(-12, -3, 100)
    # Reb = 20: eps = 20 * nu * N2_ref
    eps_crit = 20.0 * nu * N2_ref
    ax.axvline(eps_crit, color="k", lw=0.8, ls="--", alpha=0.4,
               label=f"Reb=20 (N²={N2_ref:.0e})")


def plot_temperature_profile(ds: xr.Dataset) -> plt.Figure:
    """REQ-PLOT-008: binned temperature profile annotated with regimes and staircases."""
    fig, ax = plt.subplots(figsize=(5, 8))

    # Binned CT profile
    z = ds["depth_bin"].values if "depth_bin" in ds else None
    CT = ds["CT_bin"].values if "CT_bin" in ds else None
    if z is None or CT is None:
        ax.text(0.5, 0.5, "No CTD data", transform=ax.transAxes, ha="center")
        return fig

    ax.plot(CT, z, "k-", lw=1.5, label="CT (binned)")

    # Staircase regions
    if "staircase_flag" in ds:
        sc = ds["staircase_flag"].values
        _shade_regions(ax, z, sc > 0.5, color="#aaddff", alpha=0.4, label="Staircase")

    # Turbulent mixing bins on eps grid
    if "regime" in ds and "depth_eps" in ds:
        d_eps = ds["depth_eps"].values
        reg = ds["regime"].values
        turb_z = d_eps[reg == TURBULENT]
        dd_z = d_eps[reg == DOUBLE_DIFFUSION]
        for tz in turb_z:
            ax.axhspan(tz - 1, tz + 1, color=_REGIME_COLORS[TURBULENT], alpha=0.15)
        for dz_val in dd_z:
            ax.axhspan(dz_val - 1, dz_val + 1, color=_REGIME_COLORS[DOUBLE_DIFFUSION], alpha=0.15)
        # Dummy lines for legend entries
        from matplotlib.lines import Line2D
        ax.add_line(Line2D([], [], color=_REGIME_COLORS[TURBULENT], lw=6,
                           alpha=0.3, label="Turbulent mixing"))
        ax.add_line(Line2D([], [], color=_REGIME_COLORS[DOUBLE_DIFFUSION], lw=6,
                           alpha=0.3, label="Double diffusion"))

    _depth_axis(ax)
    ax.set_xlabel("Conservative Temperature (°C)")
    ax.set_title(f"Temperature profile — {ds.attrs.get('station_name', '')}")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def _shade_regions(
    ax: plt.Axes,
    depth: np.ndarray,
    mask: np.ndarray,
    color: str,
    alpha: float,
    label: str,
) -> None:
    """Shade contiguous depth regions where mask is True."""
    if not np.any(mask):
        return
    transitions = np.diff(mask.astype(int))
    starts = list(np.where(transitions == 1)[0] + 1)
    ends = list(np.where(transitions == -1)[0] + 1)
    if mask[0]:
        starts = [0] + starts
    if mask[-1]:
        ends = ends + [len(mask)]
    for i, (s, e) in enumerate(zip(starts, ends)):
        ax.axhspan(depth[s], depth[min(e, len(depth)-1)],
                   color=color, alpha=alpha,
                   label=label if i == 0 else "_nolegend_")


# ─── multipanel profile overview ──────────────────────────────────────────────

def plot_profile_overview(ds: xr.Dataset) -> plt.Figure:
    """REQ-PLOT-010: six-panel vertical profile overview.

    Panels (left to right):
      1. Temperature — FP07 T1/T2 (fast grid) + JAC-T (slow grid)
      2. Absolute Salinity (binned)
      3. Potential density anomaly σ₀ (binned)
      4. ε best-estimate (log x-axis, eps grid)
      5. Turbidity (binned)
      6. Chlorophyll-a (binned)
    """
    fig, axes = plt.subplots(1, 6, figsize=(16, 8), sharey=True)
    station = ds.attrs.get("station_name", "")

    # ── helpers ──
    def _zf():
        return ds["depth_fast"].values if "depth_fast" in ds else None

    def _zs():
        return ds["depth_slow"].values if "depth_slow" in ds else None

    def _zb():
        return ds["depth_bin"].values if "depth_bin" in ds else None

    def _ze():
        return ds["depth_eps"].values if "depth_eps" in ds else None

    def _get(name):
        return ds[name].values if name in ds else None

    # ── panel 1: temperature ──
    ax = axes[0]
    zf, zs = _zf(), _zs()
    if zf is not None:
        for var, label, color in [("T1_cal", "FP07 T1", "#e6194b"),
                                   ("T2_cal", "FP07 T2", "#4363d8")]:
            v = _get(var)
            if v is not None:
                ax.plot(v, zf, lw=0.6, color=color, alpha=0.7, label=label)
    if zs is not None:
        v = _get("JAC_T")
        if v is not None:
            ax.plot(v, zs, lw=1.2, color="k", label="JAC-T")
    ax.set_xlabel("Temperature (°C)")
    ax.legend(fontsize=7, loc="lower right")
    ax.grid(True, alpha=0.25)

    # ── panel 2: salinity ──
    ax = axes[1]
    zb = _zb()
    v = _get("SA_bin") if zb is not None else _get("SA")
    z = zb if zb is not None else _zs()
    if v is not None and z is not None:
        ax.plot(v, z, color="#3cb44b", lw=1.5)
    ax.set_xlabel("Absolute Salinity (g/kg)")
    ax.grid(True, alpha=0.25)

    # ── panel 3: density ──
    ax = axes[2]
    v = _get("sigma0_bin") if zb is not None else _get("sigma0")
    z = zb if zb is not None else _zs()
    if v is not None and z is not None:
        ax.plot(v, z, color="#f58231", lw=1.5)
    ax.set_xlabel("σ₀ (kg m⁻³)")
    ax.grid(True, alpha=0.25)

    # ── panel 4: epsilon (log) ──
    ax = axes[3]
    ze = _ze()
    if ze is not None:
        for var, label, color, ls in [
            ("eps1",     "ε₁",    "#e6194b", "--"),
            ("eps2",     "ε₂",    "#4363d8", ":"),
            ("eps_best", "ε best","k",        "-"),
        ]:
            v = _get(var)
            if v is not None:
                valid = np.isfinite(v) & (v > 0)
                if valid.any():
                    ax.semilogx(v[valid], ze[valid], color=color, ls=ls,
                                lw=1.2, marker="o", ms=2.5, label=label)
    ax.set_xlabel("ε (W kg⁻¹)")
    ax.legend(fontsize=7, loc="lower right")
    ax.grid(True, which="both", alpha=0.25)

    # ── panel 5: turbidity ──
    ax = axes[4]
    v = _get("turbidity_bin") if zb is not None else _get("turbidity")
    z = zb if zb is not None else _zf()
    if v is not None and z is not None:
        ax.plot(v, z, color="#911eb4", lw=1.5)
    ax.set_xlabel("Turbidity (FTU)")
    ax.grid(True, alpha=0.25)

    # ── panel 6: chlorophyll ──
    ax = axes[5]
    v = _get("chlorophyll_bin") if zb is not None else _get("chlorophyll")
    z = zb if zb is not None else _zf()
    if v is not None and z is not None:
        ax.plot(v, z, color="#2ecc71", lw=1.5)
    ax.set_xlabel("Chlorophyll-a (ppb)")
    ax.grid(True, alpha=0.25)

    # ── shared y-axis ──
    axes[0].invert_yaxis()
    axes[0].set_ylabel("Pressure (dbar)")
    fig.suptitle(f"Profile overview — {station}", fontsize=11)
    fig.tight_layout()
    return fig


# ─── master function ────────────────────────────────────────────────────────────

def plot_all(
    ds: xr.Dataset,
    output_dir: Path | str,
    gade_T_AW: float | None = None,
    gade_S_AW: float | None = None,
    gade_T_ice: float = -2.0,
    ts_scalar: str = "turbidity_bin",
) -> dict[str, Path]:
    """Generate and save all diagnostic figures for one profile.

    Parameters
    ----------
    ds         : processed profile Dataset (from netCDF)
    output_dir : directory to save PNG files
    gade_T_AW  : Atlantic Water temperature end-member (default: max in profile)
    gade_S_AW  : Atlantic Water salinity end-member (default: max in profile)
    gade_T_ice : ice temperature for Gade line (°C, default -2)
    ts_scalar  : variable name to colour the T-S scalar plot (default 'turbidity_bin')

    Returns
    -------
    dict mapping plot name → Path of saved file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: dict[str, Path] = {}

    def _save(fig: plt.Figure, name: str) -> None:
        path = output_dir / f"{name}.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        saved[name] = path

    _save(plot_profile_overview(ds), "profile_overview")
    _save(plot_ts(ds), "ts_diagram")
    _save(plot_ts_gade(ds, T_AW=gade_T_AW, S_AW=gade_S_AW, T_ice=gade_T_ice), "ts_gade")
    if ts_scalar in ds:
        _save(plot_ts_scalar(ds, scalar_var=ts_scalar,
                             T_AW=gade_T_AW, S_AW=gade_S_AW, T_ice=gade_T_ice),
              f"ts_{ts_scalar}")
    _save(plot_epsilon_profiles(ds), "epsilon_profiles")
    _save(plot_chi_profiles(ds), "chi_profiles")
    _save(plot_chi_epsilon_diagram(ds), "chi_epsilon_diagram")
    _save(plot_temperature_profile(ds), "temperature_profile")

    return saved
