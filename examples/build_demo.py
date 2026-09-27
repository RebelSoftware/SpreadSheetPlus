#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Build the SpreadSheetPlus demonstration document - a small bolt family.

Run it inside FreeCAD, with this repository on the module path::

    freecadcmd -M <repo-root> examples/build_demo.py    # headless
    freecad    -M <repo-root> examples/build_demo.py    # with the GUI (nicer)

With the addon installed (or symlinked) into ``Mod/`` the ``-M`` is not needed,
and the script can also be run from *Macro → Macros… → execute*.

It writes ``SpreadSheetPlus-demo.FCStd`` next to this file. ``examples/README.md``
has the guided tour of the result; the point of the script itself is to show how
little code the whole thing takes:

* one configuration table (``BoltTable``) - rows are configurations, columns are
  parameters. This is the single source of truth.
* ``Bolt`` - a PartDesign part carrying a ``ConfigRef`` (``BoltConfig``). Its
  features only ever reference *the reference* (``BoltConfig.ShankLength``),
  never the spreadsheet, so the part follows whichever row the reference
  selects.
* ``Spacer`` - a second part with its own reference and its own row: one table,
  many parts, nothing copied.
* two ``App::Link`` variants of ``Bolt`` - each one chose its own row through the
  link's mirrored property, which is what makes FreeCAD copy the part for it.
"""

from __future__ import annotations

import os

import FreeCAD as App

from freecad.spreadsheetplus import config_ref
from freecad.spreadsheetplus.master_sheet import MasterSheet

#: Document name, and the file written next to this script.
DOCUMENT = "SpreadSheetPlusDemo"
FILENAME = "SpreadSheetPlus-demo.FCStd"

#: Row 1 of the table is free text (the sheet's own "A1" title).
TITLE = "Bolt family - edit a row here and every part that uses it follows"

#: The parameters - one column each, named in row 2.
PARAMETERS = (
    "Designation",       # text (kept as App::PropertyString)
    "ShankDiameter",     # length -> App::PropertyLength
    "ShankLength",       # length
    "ThreadPitch",       # length
    "HeadAcrossFlats",   # length
    "HeadHeight",        # length
    "HexHead",           # bool -> App::PropertyBool
)

#: The configurations - one row each, with a value per parameter.
#:
#: Lengths carry their unit ("6 mm"), so the reference exposes them as quantity
#: properties and expressions can use them directly - no ``* 1 mm``. Numbers
#: without a unit work too; they are read as millimetres in a length context.
CONFIGURATIONS = {
    "M6x20": ("M6 x 20", "6 mm", "20 mm", "1 mm", "10 mm", "4 mm", True),
    "M6x30": ("M6 x 30", "6 mm", "30 mm", "1 mm", "10 mm", "4 mm", True),
    "M8x20": ("M8 x 20", "8 mm", "20 mm", "1.25 mm", "13 mm", "5.3 mm", True),
    "M8x40": ("M8 x 40", "8 mm", "40 mm", "1.25 mm", "13 mm", "5.3 mm", True),
    "M8x20s": ("M8 x 20 socket", "8 mm", "20 mm", "1.25 mm", "13 mm", "8 mm", False),
}

#: The rows the demo picks for the template, the spacer and the two variants
#: (row, object name, label).
BOLT_ROW = "M6x20"
SPACER_ROW = "M8x20"
VARIANT_ROWS = (("M6x30", "BoltM6x30", "Bolt M6x30"), ("M8x20s", "BoltSocket", "Bolt M8 x 20 socket"))


def build_table(doc):
    """Create the master table: one row per configuration, one per parameter."""
    master = MasterSheet.create(doc, name="BoltTable")
    master.set_title(TITLE)
    for parameter in PARAMETERS:
        master.add_parameter(parameter)
    for configuration, values in CONFIGURATIONS.items():
        master.add_configuration(configuration)
        for parameter, value in zip(PARAMETERS, values):
            master.set_value(configuration, parameter, value)
    return master


def add_reference(doc, container, master, configuration, name):
    """Put a ConfigRef for *configuration* into *container*.

    The reference is a normal child of the part, so a variant of that part
    carries its own - which is what lets several variants select different rows.
    """
    ref = config_ref.create(doc, master.sheet, configuration, name=name)
    container.addObject(ref)
    return ref


def build_bolt(doc, master, configuration):
    """The bolt: two interchangeable head styles plus a shank, all from the table.

    Only the numeric/boolean parameters are used; the ``Designation`` column
    shows up as a text property on the reference, ready for a label or a report.

    Layout: the origin is the underside of the head. The head grows upward from
    Z=0, the shank hangs downward from Z=0, and both are centred on the Z axis.
    """
    body = doc.addObject("PartDesign::Body", "Bolt")
    ref = add_reference(doc, body, master, configuration, "BoltConfig")

    # --- Head ---------------------------------------------------------------
    # A hex head is a regular hexagonal prism; "across flats" is the distance
    # between opposite faces, so the circumradius is A/F / sqrt(3).
    hex_head = body.newObject("PartDesign::AdditivePrism", "HexHead")
    hex_head.setExpression("Polygon", "6")
    hex_head.setExpression("Circumradius", "BoltConfig.HeadAcrossFlats / sqrt(3)")
    hex_head.setExpression("Height", "BoltConfig.HeadHeight")
    hex_head.setExpression("Suppressed", "BoltConfig.HexHead == False")

    # A socket head is a cylinder of the same height, centred on Z.
    socket_head = body.newObject("PartDesign::AdditiveCylinder", "SocketHead")
    socket_head.setExpression("Radius", "BoltConfig.HeadAcrossFlats / 2")
    socket_head.setExpression("Height", "BoltConfig.HeadHeight")
    socket_head.setExpression("Suppressed", "BoltConfig.HexHead")

    # --- Shank --------------------------------------------------------------
    shank = body.newObject("PartDesign::AdditiveCylinder", "Shank")
    shank.setExpression("Radius", "BoltConfig.ShankDiameter / 2")
    shank.setExpression("Height", "BoltConfig.ShankLength")
    shank.AttachmentSupport = [(body.Origin, "XY_Plane")]
    shank.MapMode = "FlatFace"
    shank.setExpression("AttachmentOffset.Base.z", "BoltConfig.HeadHeight")
    # Attach the shank's flat face to the body's XY_Plane - the underside of the
    # head - then lift it by the head height. Going through the body's own plane
    # rather than to the head feature itself keeps the shank independent of
    # which head style is switched on.

    chamfer = body.newObject("PartDesign::Chamfer", "TipChamfer")
    chamfer.Base = (shank, [])   # empty sub-element list
    chamfer.UseAllEdges = True
    chamfer.Size = "0.5 mm"

    return body, ref


def build_spacer(doc, master, configuration):
    """A second part: same table, its own ConfigRef, its own row."""
    body = doc.addObject("PartDesign::Body", "Spacer")
    ref = add_reference(doc, body, master, configuration, "SpacerConfig")

    tube = body.newObject("PartDesign::AdditiveCylinder", "Tube")
    tube.setExpression("Radius", "SpacerConfig.HeadAcrossFlats / 2")
    tube.setExpression("Height", "SpacerConfig.HeadHeight * 2")

    bore = body.newObject("PartDesign::SubtractiveCylinder", "Bore")
    bore.setExpression("Radius", "SpacerConfig.ShankDiameter / 2")
    bore.setExpression("Height", "SpacerConfig.HeadHeight * 2")
    return body, ref


def build_variant(doc, source, selector, row, name, label):
    """Link *source* and give it its own row - an independent variant.

    The row is changed on the **link**, not on the part: FreeCAD copies the
    linked object into an independent one as soon as one of the link's own
    mirrored properties changes, which is exactly what "copy on change" means.
    Changing the row on the part instead would move the part itself (and every
    variant that still follows it).

    What FreeCAD copies along is the *part* and its dependencies - but not the
    table: every master sheet is marked as shared
    (`master_sheet.keep_shared()`), so the copied reference keeps reading the one
    master and later edits there reach this variant too. Only the row is its own.
    """
    link = doc.addObject("App::Link", name)
    link.Label = label
    link.LinkedObject = source
    link.LinkCopyOnChange = "Enabled"
    doc.recompute()  # let FreeCAD mirror the part's selectors onto the link

    setattr(link, selector, row)
    doc.recompute()  # ...and now it copies, so this variant keeps its own row
    link.LinkedObject.Label = f"{label} (copy)"
    return link


def spread_out(obj, x):
    """Move *obj* aside, so the demo does not stack every part at the origin."""
    obj.Placement = App.Placement(App.Vector(x, 0, 0), App.Rotation())
    return obj


def main() -> None:
    doc = App.newDocument(DOCUMENT)
    doc.Label = "SpreadSheetPlus demo - bolt family"

    master = build_table(doc)
    bolt, bolt_ref = build_bolt(doc, master, BOLT_ROW)

    spacer, _ = build_spacer(doc, master, SPACER_ROW)
    spread_out(spacer, 30)

    # The name the part uses for its selector - and so the name of the mirrored
    # property a link carries.
    selector = config_ref.slot_name(bolt_ref)
    for index, (row, name, label) in enumerate(VARIANT_ROWS):
        spread_out(build_variant(doc, bolt, selector, row, name, label), 60 + 30 * index)

    doc.recompute()
    if App.GuiUp:
        # Frame the result when this runs in a GUI. Guarded because a GUI
        # without a GL context (offscreen, CI) has no view to fit.
        try:
            import FreeCADGui as Gui

            view = Gui.ActiveDocument.ActiveView
            view.viewAxonometric()
            view.viewFit()
        except Exception as exc:  # noqa: BLE001
            print(f"(could not frame the 3D view: {exc})", flush=True)

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), FILENAME)
    doc.saveAs(path)

    print(f"Wrote {path}", flush=True)
    print(f"  table:  {len(CONFIGURATIONS)} configurations x {len(PARAMETERS)} parameters", flush=True)
    for link in doc.Objects:
        if link.TypeId == "App::Link":
            print(f"  variant: {link.Label} -> {selector} = {getattr(link, selector)!r}", flush=True)
    print("See examples/README.md for the guided tour.", flush=True)


main()
