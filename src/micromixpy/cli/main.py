"""Command-line interface for MicroMixPy VMP processing pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..config import load_config, write_template, show_config, CONFIG_PATH
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
    p.add_argument("--config", default=None, metavar="PATH",
                   help=f"Config file path (default: {CONFIG_PATH})")
    sub = p.add_subparsers(dest="command", required=True)

    # ---- config ----
    cfg_p = sub.add_parser("config", help="Manage configuration file.")
    cfg_group = cfg_p.add_mutually_exclusive_group(required=True)
    cfg_group.add_argument("--init", action="store_true",
                           help="Write config template to the config file path.")
    cfg_group.add_argument("--show", action="store_true",
                           help="Print effective configuration (file + defaults).")
    cfg_p.add_argument("--force", action="store_true",
                       help="Overwrite existing config file (use with --init).")

    # ---- process ----
    proc = sub.add_parser("process", help="Process one or more .mat files.")
    proc.add_argument("mat_files", nargs="+", help=".mat file(s) to process")
    proc.add_argument("--metadata", default=None,
                      help="Path to vmp_positions_corrected.csv (overrides config)")
    proc.add_argument("--output-dir", default=None,
                      help="Directory to write output .nc files (overrides config)")
    proc.add_argument("--profiles", nargs="+", type=int, default=None,
                      help="Profile numbers to process (default: all found in file)")
    proc.add_argument("--dz-bin", type=float, default=None,
                      help="Bin size for slow profiles (dbar)")
    proc.add_argument("--dz-eps", type=float, default=None,
                      help="Segment size for epsilon computation (dbar)")
    proc.add_argument("--nperseg", type=int, default=None,
                      help="Welch segment length (samples, default 512=1s at 512Hz)")
    proc.add_argument("--chi-method", choices=["batchelor", "direct"], default=None,
                      help="Method for chi estimation: 'batchelor' (default) or 'direct'.")
    proc.add_argument("--coherence-threshold", type=float, default=None, metavar="COH",
                      help="Inter-thermistor coherence threshold for chi quality flag (0-1).")
    proc.add_argument("--exclude-above", type=float, default=None, metavar="DBAR",
                      help="Exclude epsilon/chi bins at or above this pressure (dbar).")
    proc.add_argument("--skip-missing-meta", action="store_true",
                      help="Warn but continue if a profile has no metadata entry")

    # ---- plot ----
    plot_p = sub.add_parser("plot", help="Generate diagnostic plots from a processed netCDF file.")
    plot_p.add_argument("nc_files", nargs="+", help="Processed .nc file(s)")
    plot_p.add_argument("--output-dir", default=None,
                        help="Directory for plots (default: alongside each .nc file)")
    plot_p.add_argument("--gade-T-AW", type=float, default=None, metavar="DEGC",
                        help="Atlantic Water temperature end-member for Gade line")
    plot_p.add_argument("--gade-S-AW", type=float, default=None, metavar="G_KG",
                        help="Atlantic Water salinity end-member")
    plot_p.add_argument("--gade-T-ice", type=float, default=None, metavar="DEGC",
                        help="Ice temperature for Gade line (default from config: -2°C)")
    plot_p.add_argument("--ts-scalar", default=None,
                        help="Binned variable to colour the T-S scatter plot")

    # ---- info ----
    info = sub.add_parser("info", help="Print .mat file variable summary.")
    info.add_argument("mat_file", help=".mat file to inspect")

    return p


def _cmd_config(args: argparse.Namespace) -> int:
    config_path = Path(args.config) if args.config else CONFIG_PATH
    if args.init:
        try:
            write_template(config_path, force=args.force)
            print(f"Config template written to {config_path}")
        except FileExistsError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    elif args.show:
        cfg = load_config(config_path)
        print(show_config(cfg))
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    import scipy.io as sio

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


def _resolve_mat_path(filename: str, mat_dir: str) -> Path:
    p = Path(filename)
    if p.is_absolute() or p.exists():
        return p
    if mat_dir:
        candidate = Path(mat_dir) / p
        if candidate.exists():
            return candidate
    return p


def _cmd_process(args: argparse.Namespace, cfg: dict) -> int:
    proc = cfg["processing"]
    paths = cfg["paths"]

    metadata_path = args.metadata or paths.get("metadata") or ""
    output_dir_str = args.output_dir or paths.get("output_dir") or ""
    mat_dir = paths.get("mat_dir") or ""

    dz_bin = args.dz_bin if args.dz_bin is not None else proc["dz_bin"]
    dz_eps = args.dz_eps if args.dz_eps is not None else proc["dz_eps"]
    nperseg = args.nperseg if args.nperseg is not None else proc["nperseg"]
    chi_method = args.chi_method or proc["chi_method"]
    coherence_threshold = (args.coherence_threshold if args.coherence_threshold is not None
                           else proc["coherence_threshold"])
    exclude_above = args.exclude_above if args.exclude_above is not None else proc["exclude_above"]

    if not metadata_path:
        print("ERROR: --metadata is required (or set paths.metadata in config).", file=sys.stderr)
        return 1
    if not output_dir_str:
        print("ERROR: --output-dir is required (or set paths.output_dir in config).", file=sys.stderr)
        return 1

    meta_df = load_metadata(metadata_path)
    output_dir = Path(output_dir_str)
    errors = 0

    for filename in args.mat_files:
        mat_path = _resolve_mat_path(filename, mat_dir)
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
                    dz_bin=dz_bin,
                    dz_eps=dz_eps,
                    nperseg=nperseg,
                    exclude_above_dbar=exclude_above,
                    chi_method=chi_method,
                    coherence_threshold=coherence_threshold,
                )
                out_path = output_dir / f"{mat.file_stem}_P{dc.profile_number:02d}_{station}.nc"
                write_profile_netcdf(out_path, result, profile_meta)
                print(f"→ {out_path.name}")
            except Exception as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                errors += 1

    return 1 if errors else 0


def _cmd_plot(args: argparse.Namespace, cfg: dict) -> int:
    import xarray as xr
    from ..diagnostics.plots import plot_all

    gade = cfg["gade"]
    plots = cfg["plots"]

    gade_T_AW = args.gade_T_AW if args.gade_T_AW is not None else gade.get("T_AW")
    gade_S_AW = args.gade_S_AW if args.gade_S_AW is not None else gade.get("S_AW")
    gade_T_ice = args.gade_T_ice if args.gade_T_ice is not None else gade.get("T_ice", -2.0)
    ts_scalar = args.ts_scalar or plots.get("ts_scalar", "turbidity_bin")
    output_dir_arg = args.output_dir or ""

    errors = 0
    for nc_path in args.nc_files:
        nc_path = Path(nc_path)
        try:
            ds = xr.open_dataset(nc_path)
            out_dir = Path(output_dir_arg) if output_dir_arg else nc_path.parent / nc_path.stem
            saved = plot_all(
                ds, out_dir,
                gade_T_AW=gade_T_AW,
                gade_S_AW=gade_S_AW,
                gade_T_ice=gade_T_ice,
                ts_scalar=ts_scalar,
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

    config_path = Path(args.config) if args.config else CONFIG_PATH
    cfg = load_config(config_path)

    if args.command == "config":
        sys.exit(_cmd_config(args))
    elif args.command == "info":
        sys.exit(_cmd_info(args))
    elif args.command == "process":
        sys.exit(_cmd_process(args, cfg))
    elif args.command == "plot":
        sys.exit(_cmd_plot(args, cfg))
