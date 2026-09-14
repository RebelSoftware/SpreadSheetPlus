# Development environment

How to run FreeCAD against this addon — including *headless* GUI runs — and how
to check FreeCAD's own behaviour when something is unclear.

## Running FreeCAD

The addon is a **namespace package**, so FreeCAD needs the repository root on
`sys.path`; pass it explicitly with `-M`:

```bash
freecadcmd -M /path/to/SpreadSheetPlus tests/test_sheet.py
freecadcmd -M /path/to/SpreadSheetPlus -c "import freecad.spreadsheetplus as m; print(m.__version__)"
```

Use `freecadcmd` for anything that does not need the GUI: it starts FreeCAD,
runs the script and exits. The AppImage's bundled `python` cannot import
`FreeCAD` — only `freecadcmd` / `freecad` initialise it.

Always give `-M` and the script path as **absolute** paths. A relative `-M .`
silently points at the wrong directory whenever the shell's working directory is
not the repository root, and the failure looks like "the addon isn't installed"
(`ModuleNotFoundError: freecad.spreadsheetplus`) rather than a path problem.

## Running GUI tests headlessly

> Use `tests/run_freecad_gui.sh`. Do **not** use
> `QT_QPA_PLATFORM=offscreen <AppRun> freecad …`.

The FreeCAD AppImage's `AppRun` wrapper ends with

```sh
# Fix: Use X to run on Wayland
export QT_QPA_PLATFORM=xcb
```

Because it sets that variable itself, a caller's `QT_QPA_PLATFORM=offscreen` has
**no effect**: a real window opens on the desktop and the process stays alive
after the script finishes (Qt's event loop keeps running). The terminal then
never returns and every later command queues behind it — which looks like tests
"producing no output" or hanging.

`tests/run_freecad_gui.sh` replicates AppRun's environment (`PREFIX`,
`PYTHONHOME`, `PATH_TO_FREECAD_LIBDIR`, fontconfig, SSL certs) but forces the
offscreen platform:

```bash
tests/run_freecad_gui.sh -M <repo-root> tests/test_gui.py
tests/run_freecad_gui.sh -M <repo-root> tests/test_container.py
```

* FreeCAD is found via `FREECAD_APPDIR`, else `~/Applications/squashfs-root`,
  `~/squashfs-root`, `/opt/FreeCAD/squashfs-root`.
* `FCSP_QPA_PLATFORM=<platform>` overrides the platform (e.g. `xcb` when you
  actually want to watch a run).
* `freecadcmd` can be run through it too, so headless and GUI runs share one
  environment.

Requirements for GUI scripts, or the runner hangs instead:

* close the main window and exit — `sys.exit()` alone is not enough:
  ```python
  mw = Gui.getMainWindow()
  if mw is not None:
      mw.close()
  sys.exit(0)
  ```
* `print(..., flush=True)` for progress: FreeCAD does not always flush stdout.
* wrap the run in `timeout` (`timeout 240 …`) as a safety net.

Offscreen Qt works for view providers, dialogs, commands and drag & drop entry
points (`ViewObject.dropObject`), and `Gui.ActiveDocument.ActiveView` exists, so
the "active container" of a Part/Body can be set with
`view.setActiveObject("pdbody", body)` / `view.setActiveObject("part", part)`
(see `tests/test_container.py`). It prints harmless
`QOpenGLWidget is not supported on this platform` lines.

## VS Code tasks

| Task | What it runs |
| :--- | :--- |
| FreeCAD: Run all tests | the headless suites in one loop |
| FreeCAD: Test &lt;module&gt; | one headless suite |
| FreeCAD: Test GUI | `tests/test_gui.py` (offscreen) |
| FreeCAD: Test container (GUI) | `tests/test_container.py` (offscreen) |
| Syntax check | `python3 -m py_compile` over the package and the tests |

All of them go through `tests/run_freecad_gui.sh`.

## Asking FreeCAD questions locally

Prefer a local FreeCAD **source checkout** over the web: behaviour (what a
container accepts, how drag & drop is decided) is version specific, and a full
clone lets you read the exact code a given AppImage was built from via its tag.
Even when the checkout is on 2.x development (`main`), its tags let you read the
released source you are testing against:

```bash
SRC=~/projects/FreeCad
git -C "$SRC" show 1.1.3:src/Mod/PartDesign/App/Body.cpp | sed -n '190,225p'
git -C "$SRC" grep -n "canDropObject" 1.1.3 -- src/Mod/PartDesign/Gui/ViewProviderBody.cpp
```

Where to look:

| Question | File |
| :--- | :--- |
| Which objects may live in a `PartDesign::Body`? | `src/Mod/PartDesign/App/Body.cpp` (`Body::isAllowed`), `src/Mod/PartDesign/Gui/ViewProviderBody.cpp` (`canDropObject`/`dropObject`) |
| What decides a tree drag & drop? | `src/Gui/Tree.cpp` (`dragMoveEvent`, `dropInObject`, `dropInDocument`), `src/Gui/ViewProviderGroupExtension.cpp` |
| How Python view providers are dispatched | `src/Gui/ViewProviderFeaturePython.cpp`, `src/Gui/ViewProviderFeaturePython.h` |
| Active container keys (`pdbody`, `part`) | `src/Gui/ActiveObjectList.h` |
| Spreadsheet cells, `Sheet::set`/`getContents` | `src/Mod/Spreadsheet/App/Sheet.cpp` |

A full checkout is a few GB, so it is best kept **outside** this repository.
Two workable arrangements:

* add it to the editor as a second workspace folder (File → Add Folder to
  Workspace…) — real path, nothing inside the addon, searchable for people and
  tools alike;
* or create a git-ignored symlink inside the repository
  (`ln -s ~/projects/FreeCad freecad-src`, plus `freecad-src/` in `.gitignore`).
  VS Code's search follows symlinks by default (`search.followSymlinks`), so
  this is searchable too, but the whole FreeCAD tree then sits inside the addon
  folder, where editors, file watchers and glob-based commands have to walk it,
  and it must never end up in a package.

Neither is needed for looking something up: `git show <tag>:<path>` and
`git grep <pattern> <tag> -- <path>` read the checkout in place.

## Test documents

`tests/fcsp_test_support.py:save_document()` writes generated documents to
`test_documents/` (git-ignored) so a run can be reopened and inspected by hand
in the GUI.
