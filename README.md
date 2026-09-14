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
ln -s ~/projects/SpreadSheetPlus ~/.local/share/FreeCAD/Mod/SpreadSheetPlus
```

Then restart FreeCAD and select **SpreadSheet Plus** from the workbench
selector.

To try it without installing, launch FreeCAD with an extra module path:

```bash
~/Applications/FreeCAD_1.1.3-Linux-x86_64-py311.AppImage -M ~/projects/SpreadSheetPlus
```

## Development

The importable package is `freecad.spreadsheetplus` (module `spreadsheetplus`).

| File | Purpose |
| :--- | :--- |
| `freecad/spreadsheetplus/__init__.py` | headless entry (exports `__version__`) |
| `freecad/spreadsheetplus/init_gui.py` | GUI entry: registers icons/translations/commands/workbench |
| `freecad/spreadsheetplus/workbench.py` | `SpreadSheetPlusWorkbench` |
| `freecad/spreadsheetplus/commands/` | toolbar/menu command classes |
| `freecad/spreadsheetplus/sheet.py` | `Sheet` wrapper around `Spreadsheet::Sheet` |
| `freecad/spreadsheetplus/table.py` | configuration table model |
| `freecad/spreadsheetplus/master_sheet.py` | `MasterSheet` wrapper |
| `freecad/spreadsheetplus/config_ref.py` | `ConfigRef` row-selection link |
| `freecad/spreadsheetplus/dialogs/` | Qt dialogs (table editor, configuration picker) |
| `freecad/spreadsheetplus/view_providers.py` | `ConfigRefViewProvider` |
| `freecad/spreadsheetplus/i18n.py` | `translate()` helper |
| `freecad/spreadsheetplus/resources/` | icons and translations |

## Documentation

- [Usage guide](docs/usage.md) — how to use the workbench (scripting workflow)
- [API reference](docs/api.md) — `Table`, `MasterSheet`, `ConfigRef`, `Sheet`
- [Publishing](docs/publishing.md) — release + Addon Index submission
- [Changelog](CHANGELOG.md)

### Running tests

Tests are dependency-free Python scripts that run inside FreeCAD's interpreter.
Extract the AppImage once, then:

```bash
cd ~/Applications
./FreeCAD_1.1.3-Linux-x86_64-py311.AppImage --appimage-extract
cd ~/projects/SpreadSheetPlus
~/Applications/squashfs-root/AppRun freecadcmd -M ~/projects/SpreadSheetPlus tests/test_sheet.py
```

Note: use `freecadcmd` (not the bare `python` from the AppImage) so that the
`FreeCAD` module is importable.

### Scripting API

```python
from freecad.spreadsheetplus.sheet import Sheet

sheet = Sheet.create(name="MySheet")
sheet.set("A1", 42)          # raw cell content
sheet.get("A1")              # -> "42"
sheet.set_alias("A1", "answer")
```

## License

[LGPL-2.1-or-later](LICENSE)
