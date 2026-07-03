"""Tests for the fabrication-house output profiles."""

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).parent.parent

_spec = importlib.util.spec_from_file_location(
    "fab_profiles", _ROOT / "fab_profiles.py"
)
assert _spec is not None and _spec.loader is not None
fab_profiles = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fab_profiles)  # type: ignore[union-attr]


class TestProfiles:
    """The PROFILES dict holds the per-fab-house format constants."""

    def test_output_subdirs(self):
        """Each fab house writes to its own output subfolder."""
        assert fab_profiles.PROFILES["jlcpcb"]["output_subdir"] == "jlcpcb"
        assert fab_profiles.PROFILES["pcbway"]["output_subdir"] == "pcbway"

    def test_jlcpcb_gerber_flags(self):
        """JLCPCB keeps the historical gerber/drill flags."""
        profile = fab_profiles.PROFILES["jlcpcb"]
        flags = (
            profile["gerber_protel_extensions"],
            profile["gerber_x2_format"],
            profile["gerber_include_netlist"],
            profile["drill_metric"],
        )
        assert flags == (False, True, True, False)
        assert profile["zip_include_all_files"] is False

    def test_pcbway_gerber_flags(self):
        """PCBWay uses Protel extensions, no X2, no netlist, metric drill."""
        profile = fab_profiles.PROFILES["pcbway"]
        flags = (
            profile["gerber_protel_extensions"],
            profile["gerber_x2_format"],
            profile["gerber_include_netlist"],
            profile["drill_metric"],
        )
        assert flags == (True, False, False, True)
        assert profile["zip_include_all_files"] is True

    def test_jlcpcb_headers(self):
        """JLCPCB BOM/CPL headers are unchanged from the original tool."""
        profile = fab_profiles.PROFILES["jlcpcb"]
        assert profile["bom_header"] == [
            "Comment",
            "Designator",
            "Footprint",
            "LCSC",
            "Quantity",
        ]
        assert profile["cpl_header"] == [
            "Designator",
            "Val",
            "Package",
            "Mid X",
            "Mid Y",
            "Rotation",
            "Layer",
        ]

    def test_pcbway_headers(self):
        """PCBWay BOM/CPL headers follow the PCBWay assembly template."""
        profile = fab_profiles.PROFILES["pcbway"]
        assert profile["bom_header"] == [
            "Item #",
            "Designator",
            "Qty",
            "Manufacturer",
            "Mfg Part #",
            "Description / Value",
            "Package/Footprint",
            "Type",
            "LCSC Part #",
            "Your Instructions / Notes",
        ]
        assert profile["cpl_header"] == [
            "Designator",
            "Mid X",
            "Mid Y",
            "Layer",
            "Rotation",
        ]


class TestGetProfile:
    """get_profile resolves keys with a safe fallback."""

    def test_known_keys(self):
        """Known keys return their own profile."""
        assert fab_profiles.get_profile("jlcpcb")["key"] == "jlcpcb"
        assert fab_profiles.get_profile("pcbway")["key"] == "pcbway"

    def test_unknown_key_falls_back_to_jlcpcb(self):
        """Unknown or missing keys fall back to the JLCPCB profile."""
        assert fab_profiles.get_profile("unknown")["key"] == "jlcpcb"
        assert fab_profiles.get_profile("")["key"] == "jlcpcb"
        assert fab_profiles.get_profile(None)["key"] == "jlcpcb"
