"""Tests for the configuration table model (dependency-free plain script).

Run inside FreeCAD's interpreter:

    ~/Applications/squashfs-root/AppRun freecadcmd -M ~/projects/FCSpreadSheetPlus tests/test_table.py
"""

import sys
import traceback

import FreeCAD

from freecad.fcspreadsheetplus.table import Table


def test_write_and_read():
    doc = FreeCAD.newDocument("TableTest")
    try:
        sheet = doc.addObject("Spreadsheet::Sheet", "MasterSheet")
        table = Table(sheet)

        table.set_title("This is my test Spreadsheet configuration")
        for name in ("Length", "Width", "Depth", "Enabled"):
            table.add_parameter(name)
        for name in ("TypeA", "TypeB", "TypeC"):
            table.add_configuration(name)

        data = {
            "TypeA": {"Length": 80, "Width": 40, "Depth": 10, "Enabled": True},
            "TypeB": {"Length": 85, "Width": 42, "Depth": 100, "Enabled": False},
            "TypeC": {"Length": 90, "Width": 55, "Depth": 90, "Enabled": True},
        }
        for config, row in data.items():
            for param, value in row.items():
                table.set_value(config, param, value)

        assert table.title == "This is my test Spreadsheet configuration"
        assert table.parameters() == ["Length", "Width", "Depth", "Enabled"]
        assert table.configurations() == ["TypeA", "TypeB", "TypeC"]
        assert table.get_value("TypeA", "Length") == "80"
        assert table.get_row("TypeB") == {
            "Length": "85",
            "Width": "42",
            "Depth": "100",
            "Enabled": "False",
        }
        assert table.validate() == []

        # verify the exact cell placement matches the documented layout
        # (FreeCAD reads string cells back with a leading apostrophe marker)
        def raw(addr):
            v = sheet.getContents(addr)
            return v[1:] if v.startswith("'") else v

        assert raw("A3") == "TypeA"
        assert raw("B2") == "Length"
        assert raw("E5") == "True"
    finally:
        FreeCAD.closeDocument("TableTest")


def test_add_remove():
    doc = FreeCAD.newDocument("TableTest2")
    try:
        sheet = doc.addObject("Spreadsheet::Sheet", "MasterSheet")
        table = Table(sheet)

        table.add_parameter("Length")
        table.add_configuration("TypeA")
        table.add_configuration("TypeB")
        table.set_value("TypeA", "Length", 10)
        table.set_value("TypeB", "Length", 20)

        assert table.configurations() == ["TypeA", "TypeB"]

        # removing the first configuration shifts the next one up
        table.remove_configuration("TypeA")
        assert table.configurations() == ["TypeB"]
        assert table.get_value("TypeB", "Length") == "20"

        # removing a parameter shifts later columns left
        table.add_parameter("Width")
        assert table.parameters() == ["Length", "Width"]
        table.remove_parameter("Length")
        assert table.parameters() == ["Width"]
    finally:
        FreeCAD.closeDocument("TableTest2")


def test_missing_lookup():
    doc = FreeCAD.newDocument("TableTest3")
    try:
        sheet = doc.addObject("Spreadsheet::Sheet", "MasterSheet")
        table = Table(sheet)
        table.add_parameter("Length")
        table.add_configuration("TypeA")

        for config, param in (("Nope", "Length"), ("TypeA", "Nope")):
            try:
                table.get_value(config, param)
            except KeyError:
                pass
            else:
                raise AssertionError(f"expected KeyError for ({config}, {param})")
    finally:
        FreeCAD.closeDocument("TableTest3")


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
