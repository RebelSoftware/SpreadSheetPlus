# Development environment

How to run FreeCAD against this addon — including *headless* GUI runs — and how
to check FreeCAD's own behaviour when something is unclear.

## Running FreeCAD

The addon is a **namespace package**, so FreeCAD needs the repository root on
`sys.path`; pass it explicitly with `-M`:

```bash
freecadcmd -M /path/to/SpreadSheetPlus tests/test_table.py
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

## Using codebase-memory for FreeCAD's source

The `codebase-memory-mcp` server (v0.10.8) builds a knowledge graph of a
directory — symbols, calls, includes, complexity — and answers symbol, call-path
and architecture questions from it. For "where is this defined", "who calls
this", "what does this class do", it is much quicker than reading files.

Every tool is also a CLI, which sidesteps a client's per-tool switches
(`cli <tool> --help` documents the flags; raw JSON still works but is
deprecated):

```bash
B=~/.local/bin/codebase-memory-mcp
$B cli index_repository --repo-path <dir> --mode moderate
$B cli search_graph --project <project> --query canDropObject
$B cli index_status --project <project>
$B cli check_index_coverage --project <project> --scopes '["."]'
```

The server also serves a graph UI (`--ui=true`, port 9749 by default), and
`--tool-profile=analysis|scout` restricts what an MCP client is allowed to call.

Indexed scopes for this addon (re-index after pulling new FreeCAD source):

| Project | Path | Nodes |
| :--- | :--- | ---: |
| `home-chris-projects-FreeCad-src` | whole `src` (incl. 3rdParty) | 116k |
| `home-chris-projects-FreeCad-src-Gui` | `src/Gui` — tree, view providers, commands | 16k |
| `home-chris-projects-FreeCad-src-Mod-Part` | `src/Mod/Part` — Part2DObject, features | 8k |
| `home-chris-projects-FreeCad-src-App` | `src/App` — Document, FeaturePython, links, groups | 5k |
| `home-chris-projects-FreeCad-src-Mod-PartDesign` | `src/Mod/PartDesign` — Body, its view provider | 4k |
| `home-chris-projects-FreeCad-src-Mod-Spreadsheet` | `src/Mod/Spreadsheet` — Sheet, cells | 1k |

What works well:

* `search_graph(query=…)` — keyword (BM25) over symbol names, returns
  `file_path` with line ranges. This is the workhorse.
* `get_code_snippet(qualified_name=…)` — read a symbol found above.
* `trace_path(function_name=…, direction="inbound"|"outbound")` — callers and
  callees, resolved to classes (pair it with `get_code_snippet` for the code).
* `query_graph` — raw Cypher over the graph, e.g. aggregates and hot-path
  candidates.
* `get_architecture` — package sizes and call-graph clusters; good for
  orientation, too coarse for a specific question.
* `index_status` / `check_index_coverage` — report `expected_nodes`/`edges`,
  `parse_partial` (C++ constructs the parser had to skip, with line ranges) and
  `not_indexed_files`. Treat a partial parse as "double-check in the source".

What to avoid:

* `semantic_query` is still unusable in 0.10.8. Tested against a **freshly built
  `full` index** of `src/Mod/Spreadsheet`, it returned unrelated symbols
  (colour-picker widgets, accessibility classes) with negative scores, while a
  keyword query for the same intent found `Sheet::removeRows` and friends
  exactly. Use keywords.
* The whole-`src` index is dominated by `3rdParty/` (salomesmesh, Clipper2, VTK
  shims). For a precise answer use the module project; use the full index for
  cross-module questions ("who implements `canDropObject` anywhere?"). A
  `.cbmignore` file in an indexed root can exclude paths from a scope.
* Upgrading the tool needs a fresh index for the new metrics/edges to appear
  (`delete_project` then `index_repository`); older graphs keep working for
  keyword queries.

Housekeeping:

* Each indexed root gets a `.codebase-memory/` folder (`config.json`,
  `status.json`); the graphs live in `~/.cache/codebase-memory-mcp` (the full
  `src` graph is ~550 MB — `delete_project` frees a scope you no longer need).
* `.codebase-memory/` is git-ignored in this repository, and the FreeCAD clone
  lists it in `.git/info/exclude` (a local, non-committed ignore) so indexing
  never shows up as untracked files there.
* Index a **subdirectory** rather than a whole repository: a focused index of a
  few thousand nodes gives far cleaner results, and each one takes seconds.

## Test documents

`tests/fcsp_test_support.py:save_document()` writes generated documents to
`test_documents/` (git-ignored) so a run can be reopened and inspected by hand
in the GUI.
