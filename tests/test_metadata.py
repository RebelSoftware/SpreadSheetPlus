"""Addon metadata (package.xml) tests (Phase 4, step 9).

Validates the manifest against FreeCAD's own Metadata parser and the
requirements of the FreeCAD Addon Index.

Run inside FreeCAD's interpreter:

    ~/Applications/squashfs-root/AppRun freecadcmd -M ~/projects/SpreadSheetPlus tests/test_metadata.py
"""

import sys
import traceback
from pathlib import Path

import FreeCAD

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_XML = ROOT / "package.xml"


def _metadata():
    return FreeCAD.Metadata(str(PACKAGE_XML))


def _field(item, name):
    """Read a metadata sub-item field (FreeCAD may return a dict or an object)."""
    if isinstance(item, dict):
        return item.get(name, "")
    return getattr(item, name, "")


def test_required_fields_present():
    md = _metadata()
    assert md.Name == "SpreadSheetPlus"
    assert md.Version, "version is required"
    assert md.Date, "date is required"
    assert md.Description, "description is required"
    assert md.Maintainer, "at least one maintainer is required"
    assert _field(md.Maintainer[0], "name")
    assert _field(md.Maintainer[0], "email")
    assert md.License and _field(md.License[0], "name") == "LGPL-2.1-or-later"


def test_icon_exists():
    md = _metadata()
    assert md.Icon, "an icon is expected by the Addon Index"
    assert (ROOT / md.Icon).is_file(), f"icon file not found: {md.Icon}"


def test_urls_and_branch():
    md = _metadata()
    urls = {_field(url, "type"): url for url in md.Urls}
    assert "repository" in urls
    # The repository <url> branch must match the branch the manifest lives on.
    assert _field(urls["repository"], "branch") == "main"
    assert _field(urls["repository"], "location").startswith("https://github.com/")
    assert "readme" in urls
    assert "bugtracker" in urls


def test_workbench_content_matches_code():
    md = _metadata()
    workbenches = md.Content.get("workbench", [])
    assert len(workbenches) == 1, "exactly one <workbench> content item expected"
    wb = workbenches[0]
    classname = _field(wb, "Classname")
    subdirectory = _field(wb, "Subdirectory")
    assert classname == "SpreadSheetPlusWorkbench"
    assert subdirectory == "freecad/spreadsheetplus"
    assert (ROOT / subdirectory).is_dir(), "subdirectory does not exist"

    # The declared classname must match the class defined in workbench.py.
    source = (ROOT / subdirectory / "workbench.py").read_text(encoding="utf-8")
    assert f"class {classname}" in source


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
