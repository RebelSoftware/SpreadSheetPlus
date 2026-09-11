"""GUI tests (run with the FreeCAD GUI, e.g. the offscreen platform).

Run inside FreeCAD's interpreter:

    QT_QPA_PLATFORM=offscreen ~/Applications/squashfs-root/AppRun freecad -M ~/projects/FCSpreadSheetPlus tests/test_gui.py
"""

import sys
import traceback

import FreeCAD
import FreeCADGui as Gui

import freecad.fcspreadsheetplus.init_gui  # noqa: F401  (registers commands + workbench)


def test_workbench_registered():
    assert "FCSpreadSheetPlusWorkbench" in Gui.listWorkbenches()


def test_commands_installed():
    for name in (
        "FCSpreadSheetPlus_CreateSheet",
        "FCSpreadSheetPlus_CreateMasterSheet",
        "FCSpreadSheetPlus_CreateConfigRef",
        "FCSpreadSheetPlus_EditConfigTable",
        "FCSpreadSheetPlus_SwitchConfiguration",
    ):
        found = False
        try:
            found = Gui.Command.get(name) is not None
        except Exception:
            found = False
        assert found, name


def test_config_ref_view_provider():
    from freecad.fcspreadsheetplus.master_sheet import MasterSheet
    from freecad.fcspreadsheetplus.config_ref import create as create_config_ref
    from freecad.fcspreadsheetplus.view_providers import ConfigRefViewProvider

    doc = FreeCAD.newDocument("GuiTest")
    try:
        master = MasterSheet.create(doc, name="MasterSheet")
        master.add_parameter("Length")
        master.add_configuration("TypeA")
        master.set_value("TypeA", "Length", 80)

        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        assert isinstance(ref.ViewObject.Proxy, ConfigRefViewProvider)
        assert ref.Length == 80
    finally:
        FreeCAD.closeDocument("GuiTest")


def test_table_editor_loads_and_writes():
    from freecad.fcspreadsheetplus.master_sheet import MasterSheet
    from freecad.fcspreadsheetplus.dialogs.table_editor import TableEditorDialog

    doc = FreeCAD.newDocument("GuiTest2")
    try:
        master = MasterSheet.create(doc, name="MasterSheet")
        for param in ("Length", "Width"):
            master.add_parameter(param)
        for config in ("TypeA", "TypeB"):
            master.add_configuration(config)
        master.set_value("TypeA", "Length", 80)
        master.set_value("TypeB", "Length", 85)

        dialog = TableEditorDialog(master)
        assert dialog.table.rowCount() == 2
        assert dialog.table.columnCount() == 2
        assert dialog.table.item(0, 0).text() == "80"

        dialog.table.item(0, 0).setText("123")
        dialog._write_back()
        assert master.get_value("TypeA", "Length") == "123"
        dialog.close()
    finally:
        FreeCAD.closeDocument("GuiTest2")


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

    mw = Gui.getMainWindow()
    if mw is not None:
        mw.close()

    sys.exit(1 if failures else 0)


# NOTE: FreeCAD executes scripts with __name__ set to the script's basename
# (not "__main__"), so main() is called unconditionally.
main()
