# Publishing to the FreeCAD Addon Index

FCSpreadSheetPlus is distributed through FreeCAD's built-in **Addon Manager**,
which reads the `package.xml` manifest from this repository and an index
maintained by the FreeCAD project.

Reference: [Addon Academy — Publishing / Indexed][indexed], plus the
[Manifest][manifest] and [Qualities][qualities] topics.

## 1. Manifest (`package.xml`)

The manifest at the repository root must stay accurate:

- `<name>`, `<version>`, `<date>`, `<description>`, `<maintainer>`, `<license>`.
- `<url type="repository" branch="main">` — the `branch` attribute must match
  the branch the manifest lives on.
- `<url type="readme">`, `<url type="documentation">`, `<url type="bugtracker">`,
  `<icon>`, `<tag>`.
- `<content><workbench>` with a `<classname>` matching the workbench class in
  `freecad/fcspreadsheetplus/workbench.py` and the `<subdirectory>` holding the
  package.

`tests/test_metadata.py` validates all of this with FreeCAD's own metadata
parser — run it before releasing.

## 2. Qualities expected by the Index

See the [Qualities][qualities] page. Highlights relevant to this addon:

- Open-source license declared **consistently** everywhere (manifest
  `<license>`, `LICENSE`, per-file SPDX headers) using exact SPDX identifiers —
  here `LGPL-2.1-or-later`.
- Python 3, using the FreeCAD-provided Qt wrappers (`from PySide import …`).
- Modern `freecad/<ModName>/` layout; no `sys.path` manipulation.
- No expensive work at import time; commands confined to this workbench.
- Repository at least 30 days old, and maintained.

## 3. Release checklist

1. Bump `<version>` and `<date>` in `package.xml`.
2. Update `CHANGELOG.md`.
3. Recompile translations (`resources/translations/README.md`).
4. Run the test suites (VS Code tasks **FreeCAD: Run all tests** and
   **FreeCAD: Test GUI**).
5. Commit and tag: `git tag -a v0.1.0 -m "0.1.0"` then `git push --tags`.
6. Recommended: keep a stable release branch that the Index tracks separate from
   active development, and tag a new release whenever that branch changes.

## 4. Submit to the Index

1. Ensure the repository is public and tagged with the `freecad` and `addon`
   GitHub topics.
2. Open an issue on the [FreeCAD Addons index][issues] choosing
   **Addon - Addition** (or post on the
   [Addons subforum](https://forum.freecad.org/viewforum.php?f=65)).
3. A FreeCAD team member reviews the addon. Once it meets the required
   qualities you are asked to tag a release, and the addon is added to the Index
   (then it appears in the Addon Manager within a day or so).

[indexed]: https://freecad.github.io/Addon-Academy/Guides/Publishing/Indexed
[manifest]: https://freecad.github.io/Addon-Academy/Topics/Structuring/Manifest
[qualities]: https://freecad.github.io/Addon-Academy/Topics/Addon-Index/Index/Qualities.html
[issues]: https://github.com/FreeCAD/Addons/issues/new/choose
