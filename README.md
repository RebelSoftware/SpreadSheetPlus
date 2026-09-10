# FCSpreadSheet2

A FreeCAD spreadsheet workbench (Python addon) similar to FreeCAD's default
Spreadsheet workbench. It reuses FreeCAD's built-in `Spreadsheet::Sheet`
objects through a thin wrapper and adds its own toolbar/menu commands.

## Requirements

- FreeCAD 1.0 or newer (tested with 1.1.3 and 2.0.1b AppImages)

## Install

Copy (or symlink) this directory into your user `Mod` folder:

```bash
ln -s ~/projects/FCSpreadSheet2 ~/.local/share/FreeCAD/Mod/FCSpreadSheet2
```

Then restart FreeCAD and select **FC SpreadSheet 2** from the workbench selector.

To try it without installing, launch FreeCAD with an extra module path:

```bash
~/Applications/FreeCAD_1.1.3-Linux-x86_64-py311.AppImage -M ~/projects/FCSpreadSheet2
```

## Development

The importable package is `freecad.fcspreadsheet2` (module `fcspreadsheet2`).

| File | Purpose |
| :--- | :--- |
| `freecad/fcspreadsheet2/__init__.py` | headless entry (exports `__version__`) |
| `freecad/fcspreadsheet2/init_gui.py` | GUI entry: registers icons/translations/commands/workbench |
| `freecad/fcspreadsheet2/workbench.py` | `FCSpreadSheet2Workbench` |
| `freecad/fcspreadsheet2/commands/` | toolbar/menu command classes |
| `freecad/fcspreadsheet2/sheet.py` | `Sheet` wrapper around `Spreadsheet::Sheet` |
| `freecad/fcspreadsheet2/resources/` | icons and translations |

### Running tests

Tests are dependency-free Python scripts that run inside FreeCAD's interpreter.
Extract the AppImage once, then:

```bash
cd ~/Applications
./FreeCAD_1.1.3-Linux-x86_64-py311.AppImage --appimage-extract
cd ~/projects/FCSpreadSheet2
~/Applications/squashfs-root/AppRun freecadcmd -M ~/projects/FCSpreadSheet2 tests/test_sheet.py
```

Note: use `freecadcmd` (not the bare `python` from the AppImage) so that the
`FreeCAD` module is importable.

### Scripting API

```python
from freecad.fcspreadsheet2.sheet import Sheet

sheet = Sheet.create(name="MySheet")
sheet.set("A1", 42)          # raw cell content
sheet.get("A1")              # -> "42"
sheet.set_alias("A1", "answer")
```

## License

[LGPL-2.1-or-later](LICENSE)
