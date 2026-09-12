"""Translation (i18n) tests (Phase 4, step 8).

Run inside FreeCAD's interpreter:

    ~/Applications/squashfs-root/AppRun freecadcmd -M ~/projects/FCSpreadSheetPlus tests/test_i18n.py
"""

import sys
import traceback

from PySide6 import QtCore

from freecad.fcspreadsheetplus import i18n
from freecad.fcspreadsheetplus.resources import Resources


def test_translation_loading():
    translations_dir = Resources.path("translations")
    translator = QtCore.QTranslator()
    assert translator.load("FCSpreadSheetPlus_de.qm", translations_dir), (
        f"failed to load FCSpreadSheetPlus_de.qm from {translations_dir}"
    )

    app = QtCore.QCoreApplication.instance()
    if app is None:
        # FreeCADCmd has no Qt application object; create one so a translator
        # can be installed (the GUI already provides a QApplication).
        app = QtCore.QCoreApplication([])
    app.installTranslator(translator)
    try:
        assert i18n.translate("FCSpreadSheetPlus", "Switch configuration") == (
            "Konfiguration wechseln"
        )
        assert i18n.translate("FCSpreadSheetPlus", "Create MasterSheet") == (
            "MasterSheet erstellen"
        )
    finally:
        app.removeTranslator(translator)


def test_untranslated_falls_back_to_source():
    # No translator installed (or the string is absent) -> source text returned.
    assert i18n.translate("FCSpreadSheetPlus", "No such string") == "No such string"


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
