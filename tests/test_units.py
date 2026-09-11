"""Unit-aware ConfigRef tests (Phase 4, step 2).

Run inside FreeCAD's interpreter:

    ~/Applications/squashfs-root/AppRun freecadcmd -M ~/projects/FCSpreadSheetPlus tests/test_units.py
"""

import sys
import traceback

import FreeCAD

from freecad.fcspreadsheetplus.master_sheet import MasterSheet
from freecad.fcspreadsheetplus.config_ref import create as create_config_ref
from fcsp_test_support import save_document


def test_length_quantity():
    doc = FreeCAD.newDocument("UnitsLength")
    try:
        master = MasterSheet.create(doc, name="MasterSheet")
        master.add_parameter("Length")
        master.add_configuration("TypeA")
        master.add_configuration("TypeB")
        master.set_value("TypeA", "Length", "80 mm")
        master.set_value("TypeB", "Length", "0.1 m")  # same dimension, other unit

        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()

        assert ref.getTypeIdOfProperty("Length") == "App::PropertyLength"
        assert ref.Length.Value == 80.0
        assert ref.Length.Unit.Type == "Length"

        ref.Configuration = "TypeB"
        doc.recompute()
        assert ref.Length.Value == 100.0  # 0.1 m -> 100 mm
    finally:
        save_document(doc, "units_length")
        FreeCAD.closeDocument("UnitsLength")


def test_angle_and_mass():
    doc = FreeCAD.newDocument("UnitsAngle")
    try:
        master = MasterSheet.create(doc, name="MasterSheet")
        master.add_parameter("Angle")
        master.add_parameter("Weight")
        master.add_configuration("TypeA")
        master.set_value("TypeA", "Angle", "45 deg")
        master.set_value("TypeA", "Weight", "3 kg")

        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()

        assert ref.getTypeIdOfProperty("Angle") == "App::PropertyAngle"
        assert ref.getTypeIdOfProperty("Weight") == "App::PropertyMass"
        assert ref.Angle.Value == 45.0
        assert ref.Weight.Value == 3.0
    finally:
        save_document(doc, "units_angle_mass")
        FreeCAD.closeDocument("UnitsAngle")


def test_expression_uses_unit_directly():
    doc = FreeCAD.newDocument("UnitsExpr")
    try:
        master = MasterSheet.create(doc, name="MasterSheet")
        master.add_parameter("Length")
        master.add_configuration("TypeA")
        master.set_value("TypeA", "Length", "80 mm")

        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        box = doc.addObject("Part::Box", "Box")
        box.setExpression("Length", "ConfigRefA.Length")  # no *1mm needed
        doc.recompute()

        assert abs(box.Length.Value - 80) < 1e-9
    finally:
        save_document(doc, "units_expression")
        FreeCAD.closeDocument("UnitsExpr")


def test_mixed_units_fallback_to_string():
    doc = FreeCAD.newDocument("UnitsMixed")
    try:
        master = MasterSheet.create(doc, name="MasterSheet")
        master.add_parameter("Value")
        master.add_configuration("TypeA")
        master.add_configuration("TypeB")
        master.set_value("TypeA", "Value", "80 mm")
        master.set_value("TypeB", "Value", "3 kg")  # different dimension

        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()

        assert ref.getTypeIdOfProperty("Value") == "App::PropertyString"
        assert isinstance(ref.Value, str)
    finally:
        save_document(doc, "units_mixed")
        FreeCAD.closeDocument("UnitsMixed")


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
