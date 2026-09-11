# Using FCSpreadSheetPlus

FCSpreadSheetPlus stores a single **configuration table** in a spreadsheet and lets
many parts share it. Each part links to the spreadsheet and selects one row (a
"configuration") by name — so a parameter change is made once, at the master.

> The GUI commands are available once the workbench is loaded (Phase 3). You can
> also script everything from the FreeCAD Python console or a macro. The addon
> must be installed/symlinked into `Mod/` or launched with `-M <repo>` so
> `freecad.fcspreadsheetplus` is importable.

## Using the GUI

After loading the workbench, a **FC SpreadSheet Plus** toolbar and menu appear:

| Command | What it does |
| :--- | :--- |
| Create Master Sheet | Create a new `MasterSheet` in the active document. |
| Create ConfigRef | Turn the selected `Spreadsheet::Sheet` into a `ConfigRef` (selects the first configuration). |
| Edit Configuration Table | Open the table editor for the selected sheet. |
| Switch Configuration | Switch the selected `ConfigRef` to another configuration row. |
| Create Sheet | Create a plain `Spreadsheet::Sheet` (same as the default workbench). |

The table editor shows parameters as columns and configurations as rows, with
buttons to add/remove rows and columns. Changes are written back to the sheet
when you press **OK**.

## The table layout

One spreadsheet = one configuration table. The layout is fixed:

|   | A         | B       | C      | D       | E        |
|---|-----------|---------|--------|---------|----------|
| 1 | *title*   |         |        |         |          |
| 2 | *configs* | Length  | Width  | Depth   | Enabled  |
| 3 | TypeA     | 80      | 40     | 10      | True     |
| 4 | TypeB     | 85      | 42     | 100     | False    |
| 5 | TypeC     | 90      | 55     | 90      | True     |

- **Row 1** — free text (title).
- **Row 2** — parameter names, columns `B`, `C`, … (cell `A2` is a cosmetic label).
- **Column A, rows 3+** — configuration names.
- **`B3…`** — one value per (configuration, parameter).

## Quick start (scripting)

```python
import FreeCAD as App
from freecad.fcspreadsheetplus.master_sheet import MasterSheet
from freecad.fcspreadsheetplus.config_ref import create as create_config_ref

doc = App.newDocument("Project")

# 1. Create the master sheet (document level)
master = MasterSheet.create(doc, name="MasterSheet")

# 2. Define parameters (columns) and configurations (rows)
for name in ("Length", "Width", "Depth", "Enabled"):
    master.add_parameter(name)
for name in ("TypeA", "TypeB", "TypeC"):
    master.add_configuration(name)

# 3. Set values
master.set_value("TypeA", "Length", 80)
master.set_value("TypeA", "Width", 40)
master.set_value("TypeA", "Depth", 10)
master.set_value("TypeA", "Enabled", True)

# 4. Link a part to the sheet and select a row
ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
doc.recompute()

# 5. Reference the row's parameters from a part
box = doc.addObject("Part::Box", "Box")
box.setExpression("Length", "ConfigRefA.Length * 1mm")
box.setExpression("Width", "ConfigRefA.Width * 1mm")
doc.recompute()
```

`ref` now exposes `Length`, `Width`, `Depth`, `Enabled` as read-only properties.
Switch configuration with:

```python
ref.Configuration = "TypeB"
doc.recompute()
```

## Sharing one sheet across parts

Create one `ConfigRef` per part, each pointing at the same master sheet:

```python
refA = create_config_ref(doc, master.sheet, "TypeA", name="PartA_Config")
refB = create_config_ref(doc, master.sheet, "TypeB", name="PartB_Config")
refC = create_config_ref(doc, master.sheet, "TypeA", name="PartC_Config")  # same row as A
doc.recompute()
```

Editing a value at the master sheet updates every linked part on the next
recompute — there is no copy of the sheet to keep in sync.

## Cross-file: a shared library

Keep the master sheet in its own file and reference it from other files.

```python
# library.FCStd
lib = App.newDocument("Library")
master = MasterSheet.create(lib, name="MasterSheet")
master.add_parameter("Length")
master.add_configuration("TypeA")
master.set_value("TypeA", "Length", 80)
lib.saveAs("/path/to/library.FCStd")
```

```python
# project.FCStd
from freecad.fcspreadsheetplus.config_ref import create as create_config_ref
from freecad.fcspreadsheetplus.config_ref import link_master_by_path

proj = App.newDocument("Project")
proj.saveAs("/path/to/project.FCStd")   # must be saved BEFORE linking

ref = create_config_ref(proj, None, "", name="ConfigRefA")
link_master_by_path(ref, "/path/to/library.FCStd", "MasterSheet")
ref.Configuration = "TypeA"
proj.recompute()
```

Save the project; when it is reopened, FreeCAD reloads the library automatically.

## Value types

Parameters are exposed with a type inferred from their values:

| Values | Property type |
| :--- | :--- |
| all `True` / `False` (or `1` / `0`) | `App::PropertyBool` |
| all integers | `App::PropertyInteger` |
| all floats | `App::PropertyFloat` |
| all lengths (`80 mm`, `0.1 m`, …) | `App::PropertyLength` |
| all angles (`45 deg`, …) | `App::PropertyAngle` |
| all masses / areas / volumes / … | `App::PropertyMass` / `PropertyArea` / `PropertyVolume` / … |
| anything else (text, mixed units, formulas) | `App::PropertyString` |

Bare numbers are unitless: reference them with a unit in the part's
expression (`<<ConfigRefA>>.Length * 1mm`).

A quantity cell (e.g. `80 mm`) is exposed as a typed quantity property that
carries its unit, so the part can reference it directly:

```
<<ConfigRefA>>.Length        →  80 mm
```

A column mixing units (or using an unmapped unit) falls back to
`App::PropertyString`.

## Running the tests

Use the VS Code task **FreeCAD: Run all tests**, or see the README.
