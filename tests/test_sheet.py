"""Tests for the Sheet wrapper (dependency-free, plain script).

Run inside FreeCAD's interpreter:

    ~/Applications/squashfs-root/AppRun freecadcmd -M ~/projects/fcspreadsheetplus tests/test_sheet.py
"""

import sys
import traceback

import FreeCAD

from freecad.fcspreadsheetplus.sheet import Sheet


def test_create_and_cells():
    doc = FreeCAD.newDocument("FCSpreadSheetPlusTest")
    try:
        sheet = Sheet.create(doc=doc, name="S1")
        assert sheet.obj.TypeId == "Spreadsheet::Sheet"

        sheet.set("A1", 42)
        assert sheet.get("A1") == "42"
        assert sheet.get_contents() == {"A1": "42"}

        sheet.clear("A1")
        assert sheet.get_contents() == {}
    finally:
        FreeCAD.closeDocument("FCSpreadSheetPlusTest")


def test_aliases():
    doc = FreeCAD.newDocument("FCSpreadSheetPlusTest")
    try:
        sheet = Sheet.create(doc=doc, name="S1")
        sheet.set("B2", "7")
        sheet.set_alias("B2", "seven")
        assert sheet.get_alias("B2") == "seven"
        assert sheet.get_cell_from_alias("seven") == "B2"
    finally:
        FreeCAD.closeDocument("FCSpreadSheetPlusTest")


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
