"""Tests for cross-file sharing (Phase 2).

Run inside FreeCAD's interpreter:

    ~/Applications/squashfs-root/AppRun freecadcmd -M ~/projects/FCSpreadSheetPlus tests/test_cross_file.py
"""

import sys
import traceback

import FreeCAD

from freecad.fcspreadsheetplus.master_sheet import MasterSheet
from freecad.fcspreadsheetplus.config_ref import create as create_config_ref
from freecad.fcspreadsheetplus.config_ref import link_master_by_path
from fcsp_test_support import TEST_DOCUMENTS_DIR


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


def _close(doc):
    if doc is not None:
        try:
            FreeCAD.closeDocument(doc.Name)
        except Exception:
            pass


def test_cross_file_link_and_restore():
    TEST_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    lib_path = str(TEST_DOCUMENTS_DIR / "cross_file_library.FCStd")
    proj_path = str(TEST_DOCUMENTS_DIR / "cross_file_project.FCStd")

    lib = FreeCAD.newDocument("Library")
    proj = None
    reopened = None
    try:
        _build_master(lib)
        lib.saveAs(lib_path)

        # Project document links to the master sheet in the external library.
        proj = FreeCAD.newDocument("Project")
        ref = create_config_ref(proj, None, "", name="ConfigRefA")

        # The project must be saved before setting an external link, so FreeCAD
        # can compute the relative path to the library.
        proj.saveAs(proj_path)

        link_master_by_path(ref, lib_path, "MasterSheet")
        ref.Configuration = "TypeA"
        proj.recompute()

        assert ref.Length == 80
        assert ref.Width == 40

        ref.Configuration = "TypeB"
        proj.recompute()
        assert ref.Length == 85

        # Save the project (persists the external link), close everything,
        # reopen, and check the external link resolves (FreeCAD reopens the
        # library automatically).
        proj.save()
        _close(proj)
        proj = None
        _close(lib)
        lib = None

        reopened = FreeCAD.openDocument(proj_path)
        reopened.recompute()

        ref2 = reopened.getObject("ConfigRefA")
        assert ref2 is not None
        assert ref2.Configuration == "TypeB"
        assert ref2.Length == 85
        assert ref2.Width == 42
    finally:
        _close(proj)
        _close(reopened)
        _close(lib)
        # library + project remain in test_documents/ for visual review


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
