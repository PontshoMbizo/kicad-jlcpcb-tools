"""Fabrication-house output profiles.

Pure data module (no wx/pcbnew imports) so it stays unit-testable.
"""

JLCPCB = "jlcpcb"
PCBWAY = "pcbway"

DEFAULT_FAB_HOUSE = JLCPCB

PROFILES = {
    JLCPCB: {
        "key": JLCPCB,
        "display_name": "JLCPCB",
        "output_subdir": "jlcpcb",
        "gerber_protel_extensions": False,
        "gerber_x2_format": True,
        "gerber_include_netlist": True,
        "drill_metric": False,
        "zip_include_all_files": False,
        "cpl_header": [
            "Designator",
            "Val",
            "Package",
            "Mid X",
            "Mid Y",
            "Rotation",
            "Layer",
        ],
        "bom_header": ["Comment", "Designator", "Footprint", "LCSC", "Quantity"],
    },
    PCBWAY: {
        "key": PCBWAY,
        "display_name": "PCBWay",
        "output_subdir": "pcbway",
        "gerber_protel_extensions": True,
        "gerber_x2_format": False,
        "gerber_include_netlist": False,
        "drill_metric": True,
        "zip_include_all_files": True,
        "cpl_header": ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"],
        "bom_header": [
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
        ],
    },
}


def get_profile(key):
    """Return the profile dict for *key*, falling back to JLCPCB."""
    return PROFILES.get(key, PROFILES[JLCPCB])
