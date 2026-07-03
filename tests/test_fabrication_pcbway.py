"""Tests for PCBWay vs JLCPCB BOM generation in Fabrication.generate_bom."""

import csv
import importlib.util
import logging
from pathlib import Path
import sys
import types
from unittest.mock import MagicMock

_ROOT = Path(__file__).parent.parent

# Mock KiCad modules before importing fabrication
for _mod in ["pcbnew", "wx", "wx.dataview"]:
    sys.modules.setdefault(_mod, MagicMock())

# fabrication.py uses relative imports, so give it a fake parent package.  A
# dedicated package name avoids clashing with the stubbed helpers registered
# by test_fabrication_corrections.py; the real fab_profiles.py and
# footprint_helpers.py resolve through the package __path__.
_pkg = types.ModuleType("kicadplugin_pcbway")
_pkg.__path__ = [str(_ROOT)]
sys.modules["kicadplugin_pcbway"] = _pkg

_spec = importlib.util.spec_from_file_location(
    "kicadplugin_pcbway.fabrication", _ROOT / "fabrication.py"
)
assert _spec is not None and _spec.loader is not None
_fab_mod = importlib.util.module_from_spec(_spec)
_fab_mod.__package__ = "kicadplugin_pcbway"
sys.modules["kicadplugin_pcbway.fabrication"] = _fab_mod
_spec.loader.exec_module(_fab_mod)  # type: ignore[union-attr]

Fabrication = _fab_mod.Fabrication  # type: ignore[attr-defined]


class FieldStub:
    """Minimal stand-in for a KiCad footprint field."""

    def __init__(self, name, text):
        """Store the field name and text."""
        self._name = name
        self._text = text

    def GetName(self):
        """Return the field name."""
        return self._name

    def GetText(self):
        """Return the field text."""
        return self._text


class FootprintStub:
    """Minimal stand-in for a KiCad footprint."""

    def __init__(self, reference, fields=None, attributes=0):
        """Store reference, fields as (name, text) tuples and attribute bits."""
        self._reference = reference
        self._fields = [FieldStub(name, text) for name, text in (fields or [])]
        self._attributes = attributes

    def GetReference(self):
        """Return the reference designator."""
        return self._reference

    def GetFields(self):
        """Return the footprint fields."""
        return self._fields

    def GetAttributes(self):
        """Return the footprint attribute bits."""
        return self._attributes


def make_fab(tmp_path, fab_house, parts, board_footprints, lcsc_bom_cpl=True):
    """Create a bare Fabrication instance wired up for generate_bom."""
    fab = object.__new__(Fabrication)
    fab.logger = logging.getLogger("test")
    fab.filename = "board.kicad_pcb"
    fab.outputdir = str(tmp_path)
    fab.board = types.SimpleNamespace(Footprints=lambda: board_footprints)
    fab.parent = types.SimpleNamespace(
        settings={
            "general": {"fab_house": fab_house},
            "gerber": {"lcsc_bom_cpl": lcsc_bom_cpl},
        },
        store=types.SimpleNamespace(read_bom_parts=lambda: parts),
    )
    return fab


def read_bom(tmp_path):
    """Read the generated BOM CSV back as a list of rows."""
    with open(tmp_path / "BOM-board.csv", newline="", encoding="utf-8") as csvfile:
        return list(csv.reader(csvfile))


PARTS = [
    {"value": "100nF", "refs": "C1,C2", "footprint": "C_0603", "lcsc": "C1525"},
    {"value": "ESP32", "refs": "U1", "footprint": "QFN-56", "lcsc": ""},
]

FOOTPRINTS = [
    FootprintStub(
        "C1",
        fields=[("Manufacturer", "Samsung"), ("MPN", "CL10B104KB8NNNC")],
        attributes=0b10,
    ),
    FootprintStub("C2", attributes=0b10),
    FootprintStub(
        "U1",
        fields=[("Mfr", "Espressif"), ("Mfr. Part #", "ESP32-WROOM-32E")],
        attributes=0b10,
    ),
]


class TestPcbwayBom:
    """PCBWay mode writes the PCBWay assembly BOM template."""

    def test_header(self, tmp_path):
        """The header row matches the PCBWay template exactly."""
        fab = make_fab(tmp_path, "pcbway", PARTS, FOOTPRINTS)
        fab.generate_bom()
        rows = read_bom(tmp_path)
        assert rows[0] == [
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

    def test_parts_without_lcsc_are_kept(self, tmp_path):
        """Parts without an LCSC number stay even when lcsc_bom_cpl is off."""
        fab = make_fab(tmp_path, "pcbway", PARTS, FOOTPRINTS, lcsc_bom_cpl=False)
        fab.generate_bom()
        rows = read_bom(tmp_path)
        assert len(rows) == 3  # header + both parts

    def test_row_contents(self, tmp_path):
        """Item #, Qty, Manufacturer, MPN, Type and LCSC columns are filled."""
        fab = make_fab(tmp_path, "pcbway", PARTS, FOOTPRINTS)
        fab.generate_bom()
        rows = read_bom(tmp_path)
        assert rows[1] == [
            "1",
            "C1,C2",
            "2",
            "Samsung",
            "CL10B104KB8NNNC",
            "100nF",
            "C_0603",
            "SMD",
            "C1525",
            "",
        ]
        assert rows[2] == [
            "2",
            "U1",
            "1",
            "Espressif",
            "ESP32-WROOM-32E",
            "ESP32",
            "QFN-56",
            "SMD",
            "",
            "",
        ]

    def test_no_designator_splitting(self, tmp_path):
        """PCBWay rows are never split on designator length."""
        refs = ",".join(f"C{i}" for i in range(1000, 1400))
        parts = [{"value": "1k", "refs": refs, "footprint": "R_0402", "lcsc": "C1"}]
        footprints = [FootprintStub(ref) for ref in refs.split(",")]
        fab = make_fab(tmp_path, "pcbway", parts, footprints)
        fab.generate_bom()
        rows = read_bom(tmp_path)
        assert len(rows) == 2  # header + exactly one row
        assert rows[1][2] == "400"


class TestJlcpcbBomRegression:
    """JLCPCB mode output stays identical to the original behavior."""

    def test_header_and_lcsc_filter(self, tmp_path):
        """The JLC header is used and no-LCSC parts are dropped when configured."""
        fab = make_fab(tmp_path, "jlcpcb", PARTS, FOOTPRINTS, lcsc_bom_cpl=False)
        fab.generate_bom()
        rows = read_bom(tmp_path)
        assert rows[0] == ["Comment", "Designator", "Footprint", "LCSC", "Quantity"]
        assert len(rows) == 2  # header + only the LCSC part
        assert rows[1] == ["100nF", "C1,C2", "C_0603", "C1525", "2"]

    def test_designator_splitting_still_applies(self, tmp_path):
        """Long designator lists are still split into multiple JLC rows."""
        refs = ",".join(f"C{i}" for i in range(1000, 1400))
        parts = [{"value": "1k", "refs": refs, "footprint": "R_0402", "lcsc": "C1"}]
        footprints = [FootprintStub(ref) for ref in refs.split(",")]
        fab = make_fab(tmp_path, "jlcpcb", parts, footprints)
        fab.generate_bom()
        rows = read_bom(tmp_path)
        assert len(rows) > 2  # header + more than one chunk row
        assert sum(int(row[4]) for row in rows[1:]) == 400
