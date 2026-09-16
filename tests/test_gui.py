"""GUI tests (run with the FreeCAD GUI, e.g. the offscreen platform).

Run inside FreeCAD's interpreter:

    QT_QPA_PLATFORM=offscreen freecad -M <repo-root> tests/test_gui.py
"""

import sys
import traceback

import FreeCAD
import FreeCADGui as Gui

import freecad.spreadsheetplus.init_gui  # noqa: F401  (registers commands + workbench)


def test_workbench_registered():
    assert "SpreadSheetPlusWorkbench" in Gui.listWorkbenches()


def test_commands_installed():
    for name in (
        "SpreadSheetPlus_CreateMasterSheet",
        "SpreadSheetPlus_CreateConfigRef",
        "SpreadSheetPlus_SwitchConfiguration",
    ):
        found = False
        try:
            found = Gui.Command.get(name) is not None
        except Exception:
            found = False
        assert found, name


def test_config_ref_view_provider():
    from freecad.spreadsheetplus.master_sheet import MasterSheet
    from freecad.spreadsheetplus.config_ref import create as create_config_ref
    from freecad.spreadsheetplus.resources import Resources
    from freecad.spreadsheetplus.view_providers import ConfigRefViewProvider

    doc = FreeCAD.newDocument("GuiTest")
    try:
        master = MasterSheet.create(doc, name="MasterSheet")
        master.add_parameter("Length")
        master.add_configuration("TypeA")
        master.set_value("TypeA", "Length", 80)

        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        assert isinstance(ref.ViewObject.Proxy, ConfigRefViewProvider)
        assert ref.Length == 80

        # a healthy reference shows the normal tree icon
        assert ref.ViewObject.Proxy.getIcon() == Resources.icon(
            "spreadsheetplus-config.svg"
        )

        # an unresolvable configuration switches it to the warning icon
        ref.Configuration = "Nope"
        doc.recompute()
        assert ref.ViewObject.Proxy.getIcon() == Resources.icon(
            "spreadsheetplus-config-warning.svg"
        )

        ref.Configuration = "TypeA"
        doc.recompute()
        assert ref.ViewObject.Proxy.getIcon() == Resources.icon(
            "spreadsheetplus-config.svg"
        )

        # a broken master link is a warning too
        ref.Master = None
        doc.recompute()
        assert ref.ViewObject.Proxy.getIcon() == Resources.icon(
            "spreadsheetplus-config-warning.svg"
        )
    finally:
        FreeCAD.closeDocument("GuiTest")


def test_select_configuration_dialog():
    from freecad.spreadsheetplus.dialogs.select_configuration import SelectConfigurationDialog

    dlg = SelectConfigurationDialog(["TypeB", "typeC", "TypeA"], "typeA")
    names = [dlg.list.item(i).text() for i in range(dlg.list.count())]
    assert names == ["TypeA", "TypeB", "typeC"]  # sorted by lower-case name
    assert dlg.list.currentItem().text() == "TypeA"  # current matched case-insensitively

    dlg._filter("typeb")
    visible = [
        dlg.list.item(i).text()
        for i in range(dlg.list.count())
        if not dlg.list.item(i).isHidden()
    ]
    assert visible == ["TypeB"]
    assert dlg.selected() == "TypeB"
    dlg.close()


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
