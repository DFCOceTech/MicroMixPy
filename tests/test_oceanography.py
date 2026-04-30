"""Unit tests for oceanographic property modules.

REQ-OCEAN-001: CT, SA, sigma0 computed via TEOS-10 for realistic Arctic values.
REQ-OCEAN-002: Thorpe scale is zero for a stably-stratified profile.
REQ-OCEAN-003: Thorpe scale is non-zero for a density inversion.
REQ-OCEAN-004: Binning returns correct number of bins and NaN for empty bins.
"""

import numpy as np
import pytest

from micromixpy.oceanography.properties import compute_ct_sa_density, compute_N2
from micromixpy.oceanography.thorpe import compute_thorpe_scales
from micromixpy.oceanography.binning import bin_to_grid


class TestOceanographicProperties:
    def test_arctic_water(self):
        """REQ-OCEAN-001: typical Arctic cold/fresh surface water gives plausible CT/SA."""
        JAC_T = np.array([2.0, 1.5, 0.5, -0.5])
        JAC_C = np.array([35.0, 36.0, 37.5, 39.0])  # mS/cm
        pressure = np.array([5.0, 20.0, 50.0, 100.0])
        CT, SA, sigma0 = compute_ct_sa_density(JAC_T, JAC_C, pressure, lat=69.0, lon=-25.0)
        assert np.all(np.isfinite(CT))
        assert np.all(np.isfinite(SA))
        assert np.all(np.isfinite(sigma0))
        assert np.all(SA > 0)
        assert np.all(sigma0 > 20.0)  # typical for seawater

    def test_density_increases_with_depth(self):
        """REQ-OCEAN-001: sigma0 should increase with depth for normal stratification."""
        JAC_T = np.array([5.0, 3.0, 1.0, 0.0])
        JAC_C = np.array([32.0, 34.0, 36.0, 38.0])
        pressure = np.array([5.0, 25.0, 60.0, 100.0])
        _, _, sigma0 = compute_ct_sa_density(JAC_T, JAC_C, pressure, lat=69.0, lon=-25.0)
        assert np.all(np.diff(sigma0) > 0), "Density should increase with depth"


class TestThorpeScales:
    def test_stable_profile_gives_zero(self):
        """REQ-OCEAN-002: monotonically stable profile → zero Thorpe scale."""
        depth = np.linspace(0, 100, 200)
        density = 1025.0 + 0.01 * depth  # stable
        _, Lt = compute_thorpe_scales(density, depth)
        assert np.allclose(Lt, 0.0, atol=1e-10)

    def test_inversion_gives_nonzero(self):
        """REQ-OCEAN-003: density inversion → non-zero Thorpe scale."""
        depth = np.linspace(0, 20, 100)
        density = 1025.0 + 0.1 * depth
        # Insert an inversion
        density[30:50] = density[50:30:-1]
        _, Lt = compute_thorpe_scales(density, depth)
        assert Lt.max() > 0.0


class TestBinning:
    def test_bin_count(self):
        """REQ-OCEAN-004: number of bins matches expected from depth range."""
        depth = np.linspace(0, 10, 1000)
        vals = np.ones(1000)
        z_bin, binned = bin_to_grid({"v": vals}, depth, dz=0.25)
        expected_bins = int((10 - 0) / 0.25)
        assert abs(len(z_bin) - expected_bins) <= 2  # allow boundary rounding

    def test_empty_bin_is_nan(self):
        """REQ-OCEAN-004: bins with no data contain NaN."""
        depth = np.array([0.5, 1.5])  # only two samples
        vals = np.array([1.0, 2.0])
        z_bin, binned = bin_to_grid({"v": vals}, depth, dz=0.25)
        # Most bins should be NaN
        assert np.isnan(binned["v"]).sum() > 0
