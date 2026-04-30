"""Load VMP-250 .mat files produced by Rockland ODAS quicklook.

ODAS quicklook fully calibrates all signals before writing the .mat file:
  - sh1, sh2   : already in s^-1 (velocity shear), including division by fall speed
  - T1_fast, T2_fast : calibrated temperature in °C
  - gradT1, gradT2   : temperature gradient in K/m (or similar, derived from pre-emphasis)
  - W_fast, W_slow   : fall speed in m/s (positive = downcast)
  - P_fast, P_slow   : pressure in dbar
  - JAC_T, JAC_C     : temperature (°C) and conductivity (mS/cm)
  - Chlorophyll      : ppb  (at fast rate — JAC backscatter sensor is 512 Hz)
  - Turbidity        : FTU  (at fast rate)

No additional shear calibration is needed after loading.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import scipy.io as sio


@dataclass
class MatData:
    """All signals extracted from one ODAS .mat file, in physical units."""

    file_stem: str
    fs_fast: float
    fs_slow: float

    # Fast-rate signals (512 Hz)
    t_fast: np.ndarray       # seconds
    P_fast: np.ndarray       # dbar
    W_fast: np.ndarray       # m/s  (positive = downcast; may blow up near surface)
    sh1: np.ndarray          # s^-1  (shear probe 1, already calibrated by ODAS)
    sh2: np.ndarray          # s^-1  (shear probe 2)
    T1_fast: np.ndarray      # °C   (FP07 thermistor 1, calibrated by ODAS)
    T2_fast: np.ndarray      # °C   (FP07 thermistor 2)
    Ax: np.ndarray           # accelerometer X
    Ay: np.ndarray           # accelerometer Y
    Chlorophyll: np.ndarray  # ppb
    Turbidity: np.ndarray    # FTU

    # Slow-rate signals (64 Hz)
    t_slow: np.ndarray       # seconds
    P_slow: np.ndarray       # dbar
    W_slow: np.ndarray       # m/s
    JAC_T: np.ndarray        # °C
    JAC_C: np.ndarray        # mS/cm


def load_mat(path: str | Path) -> MatData:
    """Load a VMP-250 ODAS .mat file and return MatData in physical units."""
    path = Path(path)
    m = sio.loadmat(str(path))

    def _r(key: str) -> np.ndarray:
        return np.asarray(m[key]).ravel().astype(np.float64)

    def _scalar(key: str) -> float:
        return float(np.asarray(m[key]).ravel()[0])

    return MatData(
        file_stem=path.stem.upper(),
        fs_fast=_scalar("fs_fast"),
        fs_slow=_scalar("fs_slow"),
        t_fast=_r("t_fast"),
        P_fast=_r("P_fast"),
        W_fast=_r("W_fast"),
        sh1=_r("sh1"),
        sh2=_r("sh2"),
        T1_fast=_r("T1_fast"),
        T2_fast=_r("T2_fast"),
        Ax=_r("Ax"),
        Ay=_r("Ay"),
        Chlorophyll=_r("Chlorophyll"),
        Turbidity=_r("Turbidity"),
        t_slow=_r("t_slow"),
        P_slow=_r("P_slow"),
        W_slow=_r("W_slow"),
        JAC_T=_r("JAC_T"),
        JAC_C=_r("JAC_C"),
    )
