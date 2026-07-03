"""Tests for the manufacturer/MPN/type field helpers in footprint_helpers."""

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).parent.parent

_spec = importlib.util.spec_from_file_location(
    "footprint_helpers", _ROOT / "footprint_helpers.py"
)
assert _spec is not None and _spec.loader is not None
footprint_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(footprint_helpers)  # type: ignore[union-attr]


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
    """Minimal stand-in for a KiCad footprint exposing GetFields()."""

    def __init__(self, fields=None, attributes=0):
        """Store fields as (name, text) tuples and the attribute bits."""
        self._fields = [FieldStub(name, text) for name, text in (fields or [])]
        self._attributes = attributes

    def GetFields(self):
        """Return the footprint fields."""
        return self._fields

    def GetAttributes(self):
        """Return the footprint attribute bits."""
        return self._attributes


class LegacyFootprintStub:
    """Stand-in for a KiCad < 8 footprint that only has GetProperties()."""

    def __init__(self, properties):
        """Store the properties dict."""
        self._properties = properties

    def GetFields(self):
        """Raise AttributeError like old pcbnew objects without fields."""
        raise AttributeError("no GetFields")

    def GetProperties(self):
        """Return the properties dict."""
        return self._properties


class TestGetManufacturer:
    """get_manufacturer reads the manufacturer name from footprint fields."""

    def test_matches_common_field_names(self):
        """Common manufacturer field spellings are all recognized."""
        for name in ("Manufacturer", "Mfr", "MFG NAME", "manufacturer_name"):
            fp = FootprintStub(fields=[(name, "Texas Instruments")])
            assert footprint_helpers.get_manufacturer(fp) == "Texas Instruments"

    def test_returns_empty_when_absent(self):
        """An unrelated field does not match."""
        fp = FootprintStub(fields=[("Datasheet", "https://example.com")])
        assert footprint_helpers.get_manufacturer(fp) == ""

    def test_skips_empty_values(self):
        """Empty field values are skipped in favor of later fields."""
        fp = FootprintStub(fields=[("Manufacturer", "  "), ("Mfr", "Vishay")])
        assert footprint_helpers.get_manufacturer(fp) == "Vishay"

    def test_properties_fallback(self):
        """KiCad < 8 footprints fall back to GetProperties()."""
        fp = LegacyFootprintStub({"Manufacturer": "Nexperia"})
        assert footprint_helpers.get_manufacturer(fp) == "Nexperia"


class TestGetMfgPartNumber:
    """get_mfg_part_number reads the MPN from footprint fields."""

    def test_matches_common_field_names(self):
        """Common MPN field spellings are all recognized."""
        for name in ("MPN", "Mfr. Part #", "Manufacturer_Part_Number", "Part Number"):
            fp = FootprintStub(fields=[(name, "NE555P")])
            assert footprint_helpers.get_mfg_part_number(fp) == "NE555P"

    def test_returns_empty_when_absent(self):
        """No MPN-like field yields an empty string."""
        fp = FootprintStub(fields=[("Value", "555")])
        assert footprint_helpers.get_mfg_part_number(fp) == ""

    def test_properties_fallback(self):
        """KiCad < 8 footprints fall back to GetProperties()."""
        fp = LegacyFootprintStub({"MPN": "STM32F103C8T6"})
        assert footprint_helpers.get_mfg_part_number(fp) == "STM32F103C8T6"


class TestGetSmdTht:
    """get_smd_tht classifies footprints from their attribute bits."""

    def test_smd(self):
        """Bit 1 set means SMD."""
        assert footprint_helpers.get_smd_tht(FootprintStub(attributes=0b10)) == "SMD"

    def test_through_hole(self):
        """Bit 0 set means through-hole."""
        assert footprint_helpers.get_smd_tht(FootprintStub(attributes=0b01)) == "TH"

    def test_unspecified(self):
        """No relevant bits set yields an empty string."""
        assert footprint_helpers.get_smd_tht(FootprintStub(attributes=0)) == ""

    def test_none_footprint(self):
        """A falsy footprint yields an empty string."""
        assert footprint_helpers.get_smd_tht(None) == ""
