"""Command-line interface for MicroMixPy VMP processing pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..io.mat_loader import load_mat
from ..io.metadata import load_metadata, get_profile_meta, list_profiles
from ..io.netcdf_writer import write_profile_netcdf
from ..processing.downcasts import extract_downcasts
from ..pipeline import process_downcast


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="micromixpy",
        description="VMP-250 microstructure processing pipeline (ODAS-like, Python).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # ---- process ----
    proc = sub.add_parser("process", help="Process one or more .mat files.")
    proc.add_argument("mat_files", nargs="+", help=".mat file(s) to process")
    proc.add_argument("--metadata", required=True, help="Path to vmp_positions_corrected.csv")
    proc.add_argument("--output-dir", required=True, help="Directory to write output .nc files")
    proc.add_argument("--profiles", nargs="+", type=int, default=None,
                      help="Profile numbers to process (default: all found in file)")
    proc.add_argument("--dz-bin", type=float, default=0.25, help="Bin size for slow profiles (dbar)")
    proc.add_argument("--dz-eps", type=float, default=2.0, help="Segment size for epsilon computation (dbar)")
    proc.add_argument("--nperseg", type=int, default=512, help="Welch segment length (samples, default 512=1s at 512Hz)")
    proc.add_argument("--chi-method", choices=["batchelor", "direct"], default="batchelor",
                      help="Method for chi estimation: 'batchelor' (default, fits Batchelor spectrum "
                           "to temperature gradient PSD, also yields eps_batchelor) or "
                           "'direct' (integrates observed PSD).")
    proc.add_argument("--coherence-threshold", type=float, default=0.5, metavar="COH",
                      help="Inter-thermistor coherence threshold for chi quality flag (0-1, default 0.5).")
    proc.add_argument("--exclude-above", type=float, default=0.0, metavar="DBAR",
                      help="Exclude epsilon/chi bins at or above this pressure (dbar ≈ m). "
                           "Use to remove ship-hull-generated turbulence near the surface.")
    proc.add_argument("--skip-missing-meta", action="store_true",
                      help="Warn but continue if a profile has no metadata entry")

    # ---- plot ----
    plot_p = sub.add_parser("plot", help="Generate diagnostic plots from a processed netCDF file.")
    plot_p.add_argument("nc_files", nargs="+", help="Processed .nc file(s)")
    plot_p.add_argument("--gade-T-AW", type=float, default=None, metavar="DEGC",
                        help="Atlantic Water temperature end-member for Gade line (default: max in profile)")
    plot_p.add_argument("--gade-S-AW", type=float, default=None, metavar="G_KG",
                        help="Atlantic Water salinity end-member (default: max in profile)")
    plot_p.add_argument("--gade-T-ice", type=float, default=-2.0, metavar="DEGC",
                        help="Ice temperature for Gade line (default: -2°C)")
    plot_p.add_argument("--ts-scalar", default="turbidity_bin",
                        help="Binned variable to colour the T-S scatter plot (default: turbidity_bin)")

    # ---- info ----
    info = sub.add_parser("info", help="Print .mat file variable summary.")
    info.add_argument("mat_file", help=".mat file to inspect")

    return p


def _cmd_info(args: argparse.Namespace) -> int:
    import scipy.io as sio
    import numpy as np

    m = sio.loadmat(args.mat_file)
    keys = sorted(k for k in m.keys() if not k.startswith("__"))
    print(f"\n{args.mat_file}")
    print("-" * 60)
    for k in keys:
        v = m[k]
        if hasattr(v, "shape"):
            print(f"  {k:30s}  {str(v.shape):20s}  {v.dtype}")
        else:
            print(f"  {k}")
    return 0


def _cmd_process(args: argparse.Namespace) -> int:
    meta_df = load_metadata(args.metadata)
    output_dir = Path(args.output_dir)
    errors = 0

    for mat_path in args.mat_files:
        mat_path = Path(mat_path)
        print(f"\nLoading {mat_path.name} …", flush=True)

        try:
            mat = load_mat(mat_path)
        except Exception as exc:
            print(f"  ERROR loading {mat_path.name}: {exc}", file=sys.stderr)
            errors += 1
            continue

        downcasts = extract_downcasts(mat)
        print(f"  Found {len(downcasts)} downcast(s).")

        target_profiles = args.profiles or list_profiles(meta_df, mat.file_stem)
        if not target_profiles:
            print(f"  WARNING: no metadata profiles found for {mat.file_stem}, processing all downcasts.")
            target_profiles = [dc.profile_number for dc in downcasts]

        for dc in downcasts:
            if dc.profile_number not in target_profiles:
                continue

            try:
                profile_meta = get_profile_meta(meta_df, mat.file_stem, dc.profile_number)
            except KeyError:
                if args.skip_missing_meta:
                    print(f"  WARNING: no metadata for profile {dc.profile_number}, using defaults.")
                    profile_meta = {
                        "station_name": f"{mat.file_stem}_P{dc.profile_number:02d}",
                        "date": "", "time": "",
                        "latitude": float("nan"), "longitude": float("nan"),
                        "file_name": mat.file_stem, "profile_number": dc.profile_number,
                    }
                else:
                    print(f"  SKIP profile {dc.profile_number}: no metadata entry.")
                    continue

            station = profile_meta["station_name"]
            print(f"  Processing profile {dc.profile_number} ({station}) …", end=" ", flush=True)

            try:
                result = process_downcast(
                    dc, mat, profile_meta,
                    dz_bin=args.dz_bin,
                    dz_eps=args.dz_eps,
                    nperseg=args.nperseg,
                    exclude_above_dbar=args.exclude_above,
                    chi_method=args.chi_method,
                    coherence_threshold=args.coherence_threshold,
                )
                out_path = output_dir / f"{mat.file_stem}_P{dc.profile_number:02d}_{station}.nc"
                write_profile_netcdf(out_path, result, profile_meta)
                print(f"→ {out_path.name}")
            except Exception as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                errors += 1

    return 1 if errors else 0


def _cmd_plot(args) -> int:
    import xarray as xr
    from ..diagnostics.plots import plot_all
    errors = 0
    for nc_path in args.nc_files:
        nc_path = Path(nc_path)
        try:
            ds = xr.open_dataset(nc_path)
            out_dir = nc_path.parent / nc_path.stem
            saved = plot_all(
                ds, out_dir,
                gade_T_AW=args.gade_T_AW,
                gade_S_AW=args.gade_S_AW,
                gade_T_ice=args.gade_T_ice,
                ts_scalar=args.ts_scalar,
            )
            ds.close()
            print(f"{nc_path.name}: {len(saved)} plots → {out_dir}/")
        except Exception as exc:
            print(f"ERROR plotting {nc_path.name}: {exc}", file=sys.stderr)
            errors += 1
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "info":
        sys.exit(_cmd_info(args))
    elif args.command == "process":
        sys.exit(_cmd_process(args))
    elif args.command == "plot":
        sys.exit(_cmd_plot(args))
