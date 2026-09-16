# SpreadSheetPlus

A FreeCAD spreadsheet workbench (Python addon) similar to FreeCAD's default
Spreadsheet workbench. It reuses FreeCAD's built-in `Spreadsheet::Sheet`
objects through a thin wrapper and adds its own toolbar/menu commands.

## Requirements

- FreeCAD 1.0 or newer (tested with 1.1.3 and 2.0.1b AppImages)

## Install

**Addon Manager** — search for *SpreadSheetPlus* in `Tools → Addon manager`
(available once the addon is listed in the FreeCAD Addon Index — see
[docs/publishing.md](docs/publishing.md)).

**Manual** — copy (or symlink) this directory into your user `Mod` folder:

```bash
ln -s <repo-root> ~/.local/share/FreeCAD/Mod/SpreadSheetPlus
```

Then restart FreeCAD and select **SpreadSheet Plus** from the workbench
selector.

To try it without installing, launch FreeCAD with an extra module path:

```bash
<freecad> -M <repo-root>
```

`<freecad>` is your FreeCAD executable (an AppImage, the extracted `AppRun`,
or a system install) and `<repo-root>` is the path to this repository.

## Development

The importable package is `freecad.spreadsheetplus` (module `spreadsheetplus`).

| File | Purpose |
| :--- | :--- |
| `freecad/spreadsheetplus/__init__.py` | headless entry (exports `__version__`) |
| `freecad/spreadsheetplus/init_gui.py` | GUI entry: registers icons/translations/commands/workbench |
| `freecad/spreadsheetplus/workbench.py` | `SpreadSheetPlusWorkbench` |
| `freecad/spreadsheetplus/commands/` | toolbar/menu command classes |
| `freecad/spreadsheetplus/table.py` | configuration table model |
| `freecad/spreadsheetplus/master_sheet.py` | `MasterSheet` wrapper |
| `freecad/spreadsheetplus/config_ref.py` | `ConfigRef` row-selection link |
| `freecad/spreadsheetplus/dialogs/` | configuration picker dialog |
| `freecad/spreadsheetplus/view_providers.py` | `ConfigRefViewProvider` |
| `freecad/spreadsheetplus/i18n.py` | `translate()` helper |
| `freecad/spreadsheetplus/resources/` | icons and translations |

## Documentation

- [Usage guide](docs/usage.md) — how to use the workbench (scripting workflow)
- [API reference](docs/api.md) — `Table`, `MasterSheet`, `ConfigRef`
- [Development environment](docs/development.md) — running FreeCAD and the tests
  (headless GUI runs, VS Code tasks, where to find FreeCAD's behaviour)
- [Publishing](docs/publishing.md) — release + Addon Index submission
- [Changelog](CHANGELOG.md)

### Running tests

Tests are dependency-free Python scripts that run inside FreeCAD's interpreter.
Run them from the repository root with the root added to the module path:

```bash
freecadcmd -M <repo-root> tests/test_table.py
```

`freecadcmd` is FreeCAD's command-line executable — for an AppImage, invoke it
as `AppRun freecadcmd …` or `./FreeCAD-….AppImage freecadcmd …`. Use `freecadcmd`
(not the bare `python` from the AppImage) so the `FreeCAD` module is importable.

The GUI tests (view providers, dialogs, dropping a `ConfigRef` into a part) need
a Qt GUI, which is why `tests/run_freecad_gui.sh` runs FreeCAD with the offscreen
Qt platform:

```bash
tests/run_freecad_gui.sh -M <repo-root> tests/test_gui.py
tests/run_freecad_gui.sh -M <repo-root> tests/test_container.py
```

The script exists because the FreeCAD AppImage's own `AppRun` wrapper forces
`QT_QPA_PLATFORM=xcb`, which overrides the caller's environment and opens a real
window instead of running headless. Point it at another FreeCAD build with
`FREECAD_APPDIR=<dir>`, and pick a different Qt platform with
`FCSP_QPA_PLATFORM=<platform>` when you actually want to watch the run.

In VS Code the tasks **FreeCAD: Run all tests** (headless), **FreeCAD: Test GUI**
and **FreeCAD: Test container (GUI)** wrap the same commands. See
[Development environment](docs/development.md) for the details, including how to
look up FreeCAD's own behaviour in a local source checkout.

### Scripting API

```python
from freecad.spreadsheetplus.master_sheet import MasterSheet

master = MasterSheet.create(name="MasterSheet")
master.add_parameter("Length")
master.add_configuration("TypeA")
master.set_value("TypeA", "Length", 80)
master.get_value("TypeA", "Length")   # -> "80"
```

## License

[LGPL-2.1-or-later](LICENSE)
