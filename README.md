# FCSpreadSheetPlus

A FreeCAD spreadsheet workbench (Python addon) similar to FreeCAD's default
Spreadsheet workbench. It reuses FreeCAD's built-in `Spreadsheet::Sheet`
objects through a thin wrapper and adds its own toolbar/menu commands.

## Requirements

- FreeCAD 1.0 or newer (tested with 1.1.3 and 2.0.1b AppImages)

## Install

Copy (or symlink) this directory into your user `Mod` folder:

```bash
ln -s ~/projects/fcspreadsheetplus ~/.local/share/FreeCAD/Mod/FCSpreadSheetPlus
```

Then restart FreeCAD and select **FC SpreadSheet 2** from the workbench selector.

To try it without installing, launch FreeCAD with an extra module path:

```bash
~/Applications/FreeCAD_1.1.3-Linux-x86_64-py311.AppImage -M ~/projects/fcspreadsheetplus
```

## Development

The importable package is `freecad.fcspreadsheetplus` (module `fcspreadsheetplus`).

| File | Purpose |
| :--- | :--- |
| `freecad/fcspreadsheetplus/__init__.py` | headless entry (exports `__version__`) |
| `freecad/fcspreadsheetplus/init_gui.py` | GUI entry: registers icons/translations/commands/workbench |
| `freecad/fcspreadsheetplus/workbench.py` | `FCSpreadSheetPlusWorkbench` |
| `freecad/fcspreadsheetplus/commands/` | toolbar/menu command classes |
| `freecad/fcspreadsheetplus/sheet.py` | `Sheet` wrapper around `Spreadsheet::Sheet` |
| `freecad/fcspreadsheetplus/table.py` | configuration table model |
| `freecad/fcspreadsheetplus/master_sheet.py` | `MasterSheet` wrapper |
| `freecad/fcspreadsheetplus/config_ref.py` | `ConfigRef` row-selection link |
| `freecad/fcspreadsheetplus/resources/` | icons and translations |

## Documentation

- [Usage guide](docs/usage.md) — how to use the workbench (scripting workflow)
- [API reference](docs/api.md) — `Table`, `MasterSheet`, `ConfigRef`, `Sheet`

### Running tests

Tests are dependency-free Python scripts that run inside FreeCAD's interpreter.
Extract the AppImage once, then:

```bash
cd ~/Applications
./FreeCAD_1.1.3-Linux-x86_64-py311.AppImage --appimage-extract
cd ~/projects/fcspreadsheetplus
~/Applications/squashfs-root/AppRun freecadcmd -M ~/projects/fcspreadsheetplus tests/test_sheet.py
```

Note: use `freecadcmd` (not the bare `python` from the AppImage) so that the
`FreeCAD` module is importable.

### Scripting API

```python
from freecad.fcspreadsheetplus.sheet import Sheet

sheet = Sheet.create(name="MySheet")
sheet.set("A1", 42)          # raw cell content
sheet.get("A1")              # -> "42"
sheet.set_alias("A1", "answer")
```

## License

[LGPL-2.1-or-later](LICENSE)
