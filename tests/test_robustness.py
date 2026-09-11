"""Robustness tests for ConfigRef (Phase 4, step 1).

Run inside FreeCAD's interpreter:

    ~/Applications/squashfs-root/AppRun freecadcmd -M ~/projects/FCSpreadSheetPlus tests/test_robustness.py
"""

import sys
import traceback

import FreeCAD

from freecad.fcspreadsheetplus.master_sheet import MasterSheet
from freecad.fcspreadsheetplus.config_ref import create as create_config_ref
from fcsp_test_support import save_document


def _build_master(doc):
    master = MasterSheet.create(doc, name="MasterSheet")
    for param in ("Length", "Width"):
        master.add_parameter(param)
    for config in ("TypeA", "TypeB"):
        master.add_configuration(config)
    master.set_value("TypeA", "Length", 80)
    master.set_value("TypeA", "Width", 40)
    master.set_value("TypeB", "Length", 85)
    master.set_value("TypeB", "Width", 42)
    return master


def test_configuration_valid_flag():
    doc = FreeCAD.newDocument("RobustValid")
    try:
        master = _build_master(doc)
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()

        assert ref.ConfigurationValid is True
        assert ref.ConfigurationError == ""

        # unknown row -> flagged invalid, last known values kept
        ref.Configuration = "Nope"
        doc.recompute()
        assert ref.ConfigurationValid is False
        assert "Nope" in ref.ConfigurationError
        assert ref.Length == 80

        # back to a valid row -> cleared
        ref.Configuration = "TypeB"
        doc.recompute()
        assert ref.ConfigurationValid is True
        assert ref.ConfigurationError == ""
        assert ref.Length == 85
    finally:
        save_document(doc, "robustness_valid")
        FreeCAD.closeDocument("RobustValid")


def test_broken_link_is_flagged():
    doc = FreeCAD.newDocument("RobustBroken")
    try:
        master = _build_master(doc)
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()
        assert ref.ConfigurationValid is True

        ref.Master = None
        doc.recompute()
        assert ref.ConfigurationValid is False
        assert ref.ConfigurationError == "No master spreadsheet linked"
    finally:
        save_document(doc, "robustness_broken")
        FreeCAD.closeDocument("RobustBroken")


def test_parameter_named_like_method():
    doc = FreeCAD.newDocument("RobustNames")
    try:
        master = MasterSheet.create(doc, name="MasterSheet")
        master.add_parameter("recompute")   # collides with a Python method
        master.add_parameter("Length")      # fine
        master.add_configuration("TypeA")
        master.set_value("TypeA", "recompute", 1)
        master.set_value("TypeA", "Length", 80)

        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()   # must not raise

        assert ref.Length == 80
        # "recompute" collides with an object method; it must not be exposed
        # as a managed property (exposing it would clobber the method).
        assert ref.ManagedParameters == ["Length"]
    finally:
        save_document(doc, "robustness_names")
        FreeCAD.closeDocument("RobustNames")


def main():
    tests = [
        value
        for key, value in sorted(globals().items())
        if key.startswith("test_") and callable(value)
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}", flush=True)
        except Exception:  # noqa: BLE001 - report and continue
            failures += 1
            print(f"FAIL {test.__name__}", flush=True)
            traceback.print_exc()

    print(f"{len(tests) - failures}/{len(tests)} tests passed", flush=True)
    sys.stdout.flush()
    sys.exit(1 if failures else 0)


# NOTE: FreeCADCmd executes scripts with __name__ set to the script's basename
# (not "__main__"), so main() is called unconditionally.
main()
