"""Tests for config file loading and CLI override behaviour."""

import tempfile
from pathlib import Path

import pytest

from micromixpy.config import load_config, DEFAULT_CONFIG, CONFIG_PATH


SAMPLE_TOML = """\
[paths]
mat_dir = "/data/mat_files"
metadata = "/data/metadata.csv"
output_dir = "/data/output"

[processing]
dz_bin = 0.5
dz_eps = 4.0
nperseg = 1024
exclude_above = 10.0
chi_method = "direct"
coherence_threshold = 0.3

[gade]
T_ice = -5.0

[plots]
ts_scalar = "chlorophyll_bin"
"""


class TestLoadConfig:
    def test_returns_defaults_when_file_missing(self):
        cfg = load_config(Path("/nonexistent/path.toml"))
        assert cfg == DEFAULT_CONFIG

    def test_loads_paths(self, tmp_path):
        f = tmp_path / "cfg.toml"
        f.write_text(SAMPLE_TOML)
        cfg = load_config(f)
        assert cfg["paths"]["mat_dir"] == "/data/mat_files"
        assert cfg["paths"]["metadata"] == "/data/metadata.csv"
        assert cfg["paths"]["output_dir"] == "/data/output"

    def test_loads_processing_defaults(self, tmp_path):
        f = tmp_path / "cfg.toml"
        f.write_text(SAMPLE_TOML)
        cfg = load_config(f)
        assert cfg["processing"]["dz_bin"] == pytest.approx(0.5)
        assert cfg["processing"]["chi_method"] == "direct"
        assert cfg["processing"]["nperseg"] == 1024

    def test_partial_config_merges_defaults(self, tmp_path):
        f = tmp_path / "cfg.toml"
        f.write_text("[paths]\nmat_dir = \"/my/mats\"\n")
        cfg = load_config(f)
        assert cfg["paths"]["mat_dir"] == "/my/mats"
        # Unspecified values come from DEFAULT_CONFIG
        assert cfg["processing"]["dz_eps"] == DEFAULT_CONFIG["processing"]["dz_eps"]

    def test_invalid_toml_returns_defaults(self, tmp_path):
        f = tmp_path / "bad.toml"
        f.write_text("not valid {{ toml")
        cfg = load_config(f)
        assert cfg == DEFAULT_CONFIG

    def test_default_config_path_is_home(self):
        assert CONFIG_PATH == Path.home() / ".micromixpy.toml"
