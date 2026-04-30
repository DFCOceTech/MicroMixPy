"""Load and query the VMP deployment metadata CSV."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_metadata(csv_path: str | Path) -> pd.DataFrame:
    """Load vmp_positions_corrected.csv.

    Expected columns: Station_Name, Date, Time, Lat, Lon, File_Name, Profile
    """
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    df["File_Name"] = df["File_Name"].str.strip().str.upper()
    df["Profile"] = df["Profile"].astype(int)
    return df


def get_profile_meta(df: pd.DataFrame, file_stem: str, profile_num: int) -> dict:
    """Return metadata dict for a specific file + profile number.

    Raises KeyError if the profile is not in the metadata (post-DAT_070 profiles
    are not yet in the corrected positions file).
    """
    file_stem = file_stem.upper()
    mask = (df["File_Name"] == file_stem) & (df["Profile"] == profile_num)
    rows = df[mask]
    if rows.empty:
        raise KeyError(f"No metadata for {file_stem} profile {profile_num}")
    row = rows.iloc[0]
    return {
        "station_name": str(row["Station_Name"]),
        "date": str(row["Date"]),
        "time": str(row["Time"]),
        "latitude": float(row["Lat"]),
        "longitude": float(row["Lon"]),
        "file_name": file_stem,
        "profile_number": profile_num,
    }


def list_profiles(df: pd.DataFrame, file_stem: str) -> list[int]:
    """Return all profile numbers available for a given file stem."""
    mask = df["File_Name"] == file_stem.upper()
    return sorted(df.loc[mask, "Profile"].tolist())
