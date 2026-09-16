# Using SpreadSheetPlus

SpreadSheetPlus stores a single **configuration table** in a spreadsheet and lets
many parts share it. Each part links to the spreadsheet and selects one row (a
"configuration") by name — so a parameter change is made once, at the master.

> The GUI commands are available once the workbench is loaded (Phase 3). You can
> also script everything from the FreeCAD Python console or a macro. The addon
> must be installed/symlinked into `Mod/` or launched with `-M <repo>` so
> `freecad.spreadsheetplus` is importable.

## Using the GUI

After loading the workbench, a **SpreadSheet Plus** toolbar and menu appear:

| Command | What it does |
| :--- | :--- |
| Create Master Sheet | Create a new `MasterSheet` in the active document. |
| Create ConfigRef | Turn the selected `Spreadsheet::Sheet` into a `ConfigRef` (selects the first configuration). |
| Switch Configuration | Switch the selected `ConfigRef` to another configuration row. |

The `MasterSheet` is a plain `Spreadsheet::Sheet`, so you edit the table itself
in FreeCAD's normal spreadsheet editor. Table problems (duplicate names, invalid
parameter names) are reported in two places: `MasterSheet.validate()` when you
want to check programmatically, and on every `ConfigRef` that links to the table
— `TableValid` is `False`, `TableErrors` names the problems, and the reference
gets a warning icon in the tree. A reference whose own configuration no longer
resolves is flagged the same way through `ConfigurationValid` /
`ConfigurationError`. All four fields appear together in a **Validation**
section of the property editor, separate from the `Master` / `Configuration`
inputs and the parameters exposed from the master.

**Create ConfigRef** follows FreeCAD's container convention: if a Part container
or a PartDesign Body is *active* (double-click it in the tree so its label is
bold, or use **Active object** from its context menu), the new `ConfigRef` is
created **inside** it. With no active container it is created at the document
root, and you can drag it into a container afterwards. The `MasterSheet` always
stays at the document root — it is shared between parts and must not travel with
one of them.

**Switch Configuration** opens a sorted list of configuration names with a
search box (type to filter, case-insensitive), so you pick a row instead of
typing its exact name.

## Part variants (several configurations on one part)

A part can be driven by **several** configurations at once, each from its own
master table - a bolt with a length table, a head-style table and a pitch table,
for example - and every variant picks its own row from each of them. This is what
makes a part configurable without a combinatorial row per possible part.

When a `ConfigRef` sits inside a container (a Body or a Part), the container
itself grows a **selector** property named after that ConfigRef's
`ConfigurationName`, and the ConfigRef follows it. The selectors carry FreeCAD's
`CopyOnChange` status, so an `App::Link` can mirror them and copy the part:

1. Put one `ConfigRef` per master table inside the part. The part gains one
   selector per configuration (`BoltLength`, `HeadStyle`, …) - the ConfigRef's
   `ConfigurationName` names it, and defaults to the ConfigRef's own name.
2. Select the part and **Link** it (`Std_LinkMake`), then set its
   **Link Copy On Change** to `Enabled` (or `Tracking` to follow later template
   changes).
3. The link now offers a `Configuration (ConfigRef)` group in the property
   editor with one entry per configuration. Change any of them and FreeCAD copies
   the part: that link is an independent variant with its own rows.

One template plus a handful of links gives you as many variants as you like, all
still driven by the same master tables - edit a row in a master and every part
using that row follows.

Changing a row on the **part** or on the **ConfigRef** keeps the other in step,
so *Switch Configuration* and hand edits keep working exactly as before. Two
configurations in one part need distinct `ConfigurationName` values, and the name
must not collide with an existing property of the part (`Shape`, `Tip`, …); either
case is reported in `ConfigurationError` rather than silently ignored, and that
ConfigRef then falls back to its own row.

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
- **Column A, rows 3+** — configuration names (matched **case-insensitively**:
  `TypeA` and `typea` refer to the same row).
- **`B3…`** — one value per (configuration, parameter).

## Quick start (scripting)

```python
import FreeCAD as App
from freecad.spreadsheetplus.master_sheet import MasterSheet
from freecad.spreadsheetplus.config_ref import create as create_config_ref

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

## Putting a ConfigRef inside a part (container)

A `ConfigRef` can live inside any container FreeCAD offers, so the reference
travels with the part when you copy or move it:

| Container | Accepted |
| :--- | :--- |
| `App::Part` (Part container) | yes |
| `PartDesign::Body` | yes |
| `App::DocumentObjectGroup` (Std group) | yes |

Just drag the `ConfigRef` onto the container in the tree view (or call
`part.addObject(ref)`). FreeCAD allows an object in only one container, so
dragging it from one container to another moves it. The **Create ConfigRef**
command already creates the reference in the container when one is active, so
usually there is nothing to move.

This works because FreeCAD is strict about what a `PartDesign::Body` accepts —
`PartDesign::Body::isAllowed()` only takes `PartDesign` features, datums,
`Part::Part2DObject`s, shape binders, `App::VarSet`, datum elements and local
coordinate systems. A plain `App::FeaturePython` is refused by a Body, and a
`Part::FeaturePython` is turned into the Body's *base feature*, so **new
`ConfigRef`s are created as `Part::Part2DObjectPython`** — a scripted,
geometry-less object that a Body accepts as an ordinary child (the same base
Draft uses for its objects). The geometry/attachment properties that base type
brings along are hidden in the property editor; the `ConfigRef` properties are
the visible ones.

### References created by version 0.1

`ConfigRef`s saved by version 0.1 are `App::FeaturePython` objects. They keep
working, but FreeCAD refuses to drag them into a `PartDesign::Body`, and an
object's type cannot be changed in place. Convert one with:

```python
from freecad.spreadsheetplus.config_ref import convert_to_container_type

convert_to_container_type(doc.getObject("ConfigRefA"))   # e.g. on document restore
```

The reference is rebuilt under the same internal name, keeps its label,
master sheet, configuration and parameters, and is put back into the container
it was in. Expressions that used it are re-applied, so
`ConfigRefA.Length` keeps resolving; explicit `App::Link`s to the reference are
not restored.

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
from freecad.spreadsheetplus.config_ref import create as create_config_ref
from freecad.spreadsheetplus.config_ref import link_master_by_path

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
expression (`ConfigRefA.Length * 1mm`).

A quantity cell (e.g. `80 mm`) is exposed as a typed quantity property that
carries its unit, so the part can reference it directly:

```
ConfigRefA.Length        →  80 mm
```

A column mixing units (or using an unmapped unit) falls back to
`App::PropertyString`.

## Referring to a ConfigRef in expressions

Use the object's **internal name**:

```
ConfigRefA.Length
```

FreeCAD also accepts the `<<…>>` spelling, but that one refers to the object's
**label**, not its name:

```
<<My Configuration>>.Length     # only while the label is "My Configuration"
```

Since a label is meant to be edited by the user, renaming a `ConfigRef` breaks
every `<<old label>>` reference to it (with an "object not found in expression"
error), while `ConfigRefA.Length` keeps working. Prefer the internal name — the
name is what this addon sets and what the commands and docs use.

## Running the tests

Use the VS Code tasks **FreeCAD: Run all tests** (headless),
**FreeCAD: Test GUI** and **FreeCAD: Test container (GUI)**, or see the README
for the commands. The GUI tests run FreeCAD with the offscreen Qt platform via
`tests/run_freecad_gui.sh`.
