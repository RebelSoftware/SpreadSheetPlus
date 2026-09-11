"""Tests for MasterSheet + ConfigRef (Phase 1).

Run inside FreeCAD's interpreter:

    ~/Applications/squashfs-root/AppRun freecadcmd -M ~/projects/FCSpreadSheetPlus tests/test_config_ref.py
"""

import sys
import traceback

import FreeCAD

from freecad.fcspreadsheetplus.master_sheet import MasterSheet
from freecad.fcspreadsheetplus.config_ref import create as create_config_ref
from fcsp_test_support import save_document


def _build_master(doc):
    master = MasterSheet.create(doc, name="MasterSheet")
    for param in ("Length", "Width", "Depth", "Enabled"):
        master.add_parameter(param)
    for config in ("TypeA", "TypeB", "TypeC"):
        master.add_configuration(config)
    data = {
        "TypeA": {"Length": 80, "Width": 40, "Depth": 10, "Enabled": True},
        "TypeB": {"Length": 85, "Width": 42, "Depth": 100, "Enabled": False},
        "TypeC": {"Length": 90, "Width": 55, "Depth": 90, "Enabled": True},
    }
    for config, row in data.items():
        for param, value in row.items():
            master.set_value(config, param, value)
    return master


def test_config_ref_properties():
    doc = FreeCAD.newDocument("ConfigRefTest")
    try:
        master = _build_master(doc)
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()

        assert ref.Length == 80
        assert ref.Width == 40
        assert ref.Depth == 10
        assert ref.Enabled is True

        ref.Configuration = "TypeB"
        doc.recompute()
        assert ref.Length == 85
        assert ref.Width == 42
        assert ref.Enabled is False
    finally:
        save_document(doc, "config_ref_properties")
        FreeCAD.closeDocument("ConfigRefTest")


def test_expression_read_through():
    doc = FreeCAD.newDocument("ConfigRefTest2")
    try:
        master = _build_master(doc)
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")

        box = doc.addObject("Part::Box", "Box")
        box.setExpression("Length", "ConfigRefA.Length * 1mm")
        box.setExpression("Width", "ConfigRefA.Width * 1mm")
        doc.recompute()

        assert abs(box.Length.Value - 80) < 1e-9
        assert abs(box.Width.Value - 40) < 1e-9

        ref.Configuration = "TypeB"
        doc.recompute()
        assert abs(box.Length.Value - 85) < 1e-9
        assert abs(box.Width.Value - 42) < 1e-9
    finally:
        save_document(doc, "config_ref_expression")
        FreeCAD.closeDocument("ConfigRefTest2")


def test_master_edit_propagates():
    doc = FreeCAD.newDocument("ConfigRefTest3")
    try:
        master = _build_master(doc)
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()
        assert ref.Length == 80

        # edit at the master, then recompute
        master.set_value("TypeA", "Length", 123)
        doc.recompute()
        assert ref.Length == 123
    finally:
        save_document(doc, "config_ref_master_edit")
        FreeCAD.closeDocument("ConfigRefTest3")


def test_parameters_are_read_only_in_editor():
    doc = FreeCAD.newDocument("ConfigRefTest4")
    try:
        master = _build_master(doc)
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()

        # exposed parameters are read-only in the property editor...
        assert "ReadOnly" in ref.getEditorMode("Length")
        assert "ReadOnly" in ref.getEditorMode("Enabled")

        # ...but execute() still keeps them in sync with the master
        master.set_value("TypeA", "Length", 999)
        doc.recompute()
        assert ref.Length == 999
    finally:
        save_document(doc, "config_ref_readonly")
        FreeCAD.closeDocument("ConfigRefTest4")


def test_new_column_retyped_after_values_arrive():
    doc = FreeCAD.newDocument("ConfigRefTest5")
    try:
        master = _build_master(doc)
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()

        # Simulate GUI editing: a new column's header is typed first (so the
        # column is still empty), then its value arrives in a later edit.
        master.add_parameter("Diameter2")
        doc.recompute()
        assert ref.getTypeIdOfProperty("Diameter2") == "App::PropertyString"

        master.set_value("TypeA", "Diameter2", 75)
        doc.recompute()
        assert ref.getTypeIdOfProperty("Diameter2") == "App::PropertyInteger"
        assert ref.Diameter2 == 75
    finally:
        save_document(doc, "config_ref_new_column")
        FreeCAD.closeDocument("ConfigRefTest5")


def test_configuration_names_are_case_insensitive():
    doc = FreeCAD.newDocument("ConfigRefTest6")
    try:
        master = _build_master(doc)  # TypeA, TypeB, TypeC
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()

        # lower-case lookup resolves to the stored row
        ref.Configuration = "typeb"
        doc.recompute()
        assert ref.ConfigurationValid is True
        assert ref.ConfigurationError == ""
        assert ref.Length == 85  # TypeB's Length

        # table lookups are case-insensitive too
        assert master.get_value("typeA", "Length") == "80"
        assert master.get_value("TYPEC", "Length") == "90"
    finally:
        save_document(doc, "config_ref_case_insensitive")
        FreeCAD.closeDocument("ConfigRefTest6")


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
