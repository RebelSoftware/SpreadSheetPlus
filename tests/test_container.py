"""Tests for placing a ConfigRef inside a container (part / body / group).

A ConfigRef must be a child its container accepts, and FreeCAD's containers
differ: an `App::Part` or a Std group take anything, but a `PartDesign::Body`
only takes the types listed in `PartDesign::Body::isAllowed()`. These tests
exercise the real drag-and-drop entry point used by the tree view
(`ViewObject.dropObject`) rather than just `addObject`, so a regression in the
object type is caught here.

Run with the GUI (offscreen):

    tests/run_freecad_gui.sh -M <repo-root> tests/test_container.py
"""

import sys
import traceback

import FreeCAD
import FreeCADGui as Gui

import freecad.spreadsheetplus.init_gui  # noqa: F401  (registers the commands)

from freecad.spreadsheetplus.config_ref import (
    CONTAINER_OBJECT_TYPE,
    ConfigRef,
    convert_to_container_type,
    create as create_config_ref,
    object_type,
    parent_group,
)
from fcsp_test_support import save_document


def _build_master(doc):
    from freecad.spreadsheetplus.master_sheet import MasterSheet

    master = MasterSheet.create(doc, name="MasterSheet")
    master.add_parameter("Length")
    master.add_parameter("Width")
    master.add_configuration("TypeA")
    master.add_configuration("TypeB")
    master.set_value("TypeA", "Length", 80)
    master.set_value("TypeA", "Width", 40)
    master.set_value("TypeB", "Length", 85)
    master.set_value("TypeB", "Width", 42)
    return master


def test_new_config_ref_uses_container_type():
    doc = FreeCAD.newDocument("ContainerTest1")
    try:
        master = _build_master(doc)
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        assert ref.TypeId == CONTAINER_OBJECT_TYPE, ref.TypeId
        assert object_type(doc) == CONTAINER_OBJECT_TYPE
    finally:
        FreeCAD.closeDocument("ContainerTest1")


def test_config_ref_properties_hidden():
    """The base type's geometry/attachment properties stay out of the way."""
    doc = FreeCAD.newDocument("ContainerTest2")
    try:
        master = _build_master(doc)
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        for name in ("Shape", "AttachmentSupport", "MapMode", "AttachmentOffset"):
            assert ref.getEditorMode(name) == ["Hidden"], (name, ref.getEditorMode(name))
        # the parameters themselves stay visible but read-only
        assert ref.getEditorMode("Length") == ["ReadOnly"]
    finally:
        FreeCAD.closeDocument("ContainerTest2")


def test_drop_into_part():
    doc = FreeCAD.newDocument("ContainerTest3")
    try:
        master = _build_master(doc)
        part = doc.addObject("App::Part", "Part")
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()

        assert part.ViewObject.canDropObject(ref)
        part.ViewObject.dropObject(ref)
        doc.recompute()

        assert ref in part.Group
        assert ref.Length == 80
        master.set_value("TypeA", "Length", 90)
        doc.recompute()
        assert ref.Length == 90
    finally:
        save_document(doc, "container_part")
        FreeCAD.closeDocument("ContainerTest3")


def test_drop_into_body():
    """The bug from the release checklist: a ConfigRef dragged into a Body."""
    doc = FreeCAD.newDocument("ContainerTest4")
    try:
        master = _build_master(doc)
        body = doc.addObject("PartDesign::Body", "Body")
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()

        assert body.ViewObject.canDropObject(ref), "Body refuses the ConfigRef"
        body.ViewObject.dropObject(ref)
        doc.recompute()

        assert ref in body.Group, [o.Name for o in body.Group]
        # the ConfigRef must be an ordinary child, not the body's base feature
        base = body.BaseFeature
        assert base is None or base.Name != ref.Name, base
        assert ref.Length == 80

        master.set_value("TypeA", "Length", 90)
        doc.recompute()
        assert ref.Length == 90

        # a feature of the body can use the ConfigRef in an expression
        pad = doc.addObject("PartDesign::Pad", "Pad")
        body.addObject(pad)
        pad.setExpression("Length", "ConfigRefA.Length * 1mm")
        doc.recompute()
        assert abs(pad.Length.Value - 90) < 1e-9, pad.Length
    finally:
        save_document(doc, "container_body")
        FreeCAD.closeDocument("ContainerTest4")


def test_drop_into_group():
    doc = FreeCAD.newDocument("ContainerTest5")
    try:
        master = _build_master(doc)
        group = doc.addObject("App::DocumentObjectGroup", "Group")
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()

        assert group.ViewObject.canDropObject(ref)
        group.ViewObject.dropObject(ref)
        doc.recompute()
        assert ref in group.Group
    finally:
        FreeCAD.closeDocument("ContainerTest5")


def test_move_between_containers():
    doc = FreeCAD.newDocument("ContainerTest6")
    try:
        master = _build_master(doc)
        partA = doc.addObject("App::Part", "PartA")
        partB = doc.addObject("App::Part", "PartB")
        ref = create_config_ref(doc, master.sheet, "TypeB", name="ConfigRefA")
        doc.recompute()

        partA.addObject(ref)
        doc.recompute()
        assert ref in partA.Group

        # move it from part A to part B (what a drag from one to the other does)
        partB.addObject(ref)
        doc.recompute()
        assert ref in partB.Group
        assert ref not in partA.Group  # An object lives in a single group
        assert ref.Length == 85
    finally:
        FreeCAD.closeDocument("ContainerTest6")


def test_legacy_config_ref_still_works():
    """Objects from older documents keep working after the type change."""
    doc = FreeCAD.newDocument("ContainerTest7")
    try:
        master = _build_master(doc)
        legacy = doc.addObject("App::FeaturePython", "LegacyRef")
        ConfigRef(legacy)
        legacy.Master = master.sheet
        legacy.Configuration = "TypeA"
        legacy.recompute()

        assert legacy.TypeId == "App::FeaturePython"
        assert legacy.Length == 80
        assert legacy.ConfigurationValid is True

        # FreeCAD refuses to drop a plain feature into a Body; that is why the
        # conversion helper exists. (Not asserted - this is FreeCAD's rule, not
        # ours - but reported so a future change is visible.)
        body = doc.addObject("PartDesign::Body", "Body")
        doc.recompute()
        print(
            "INFO body accepts legacy App::FeaturePython ConfigRef: "
            f"{body.ViewObject.canDropObject(legacy)}",
            flush=True,
        )
    finally:
        FreeCAD.closeDocument("ContainerTest7")


def test_convert_to_container_type():
    doc = FreeCAD.newDocument("ContainerTest8")
    try:
        master = _build_master(doc)
        legacy = doc.addObject("App::FeaturePython", "ConfigRefA")
        ConfigRef(legacy)
        legacy.Master = master.sheet
        legacy.Configuration = "TypeB"
        legacy.Label = "My Configuration"
        legacy.recompute()

        # both expression spellings: the internal name, and FreeCAD's
        # `<<label>>` form (see docs/usage.md)
        box = doc.addObject("Part::Box", "Box")
        box.setExpression("Length", "ConfigRefA.Length * 1mm")
        cylinder = doc.addObject("Part::Cylinder", "Cylinder")
        cylinder.setExpression("Radius", "<<My Configuration>>.Width * 1mm")
        doc.recompute()
        assert abs(box.Length.Value - 85) < 1e-9
        assert abs(cylinder.Radius.Value - 42) < 1e-9

        body = doc.addObject("PartDesign::Body", "Body")
        doc.recompute()

        converted = convert_to_container_type(legacy)
        assert converted is not legacy
        assert converted.TypeId == CONTAINER_OBJECT_TYPE
        assert converted.Name == "ConfigRefA"
        assert converted.Label == "My Configuration"
        assert converted.Configuration == "TypeB"
        assert converted.Length == 85

        # expressions that referenced the object keep resolving (both the
        # internal-name and the label spelling are re-applied)
        doc.recompute()
        assert abs(box.Length.Value - 85) < 1e-9, box.Length
        assert abs(cylinder.Radius.Value - 42) < 1e-9, cylinder.Radius

        # and it can now go into a Body
        assert body.ViewObject.canDropObject(converted)
        body.ViewObject.dropObject(converted)
        doc.recompute()
        assert converted in body.Group

        # converting an already-converted ref is a no-op
        assert convert_to_container_type(converted) is converted
    finally:
        save_document(doc, "container_converted")
        FreeCAD.closeDocument("ContainerTest8")


def test_parent_group_helper():
    doc = FreeCAD.newDocument("ContainerTest9")
    try:
        master = _build_master(doc)
        part = doc.addObject("App::Part", "Part")
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        doc.recompute()
        assert parent_group(ref) is None
        part.addObject(ref)
        doc.recompute()
        assert parent_group(ref) is part
    finally:
        FreeCAD.closeDocument("ContainerTest9")


def test_expression_syntax():
    """Document FreeCAD's two expression spellings for a ConfigRef.

    ``Name.Property`` uses the object's internal name (what the addon creates
    and documents); ``<<Label>>.Property`` uses the *label*, so it stops
    resolving as soon as the user relabels the object.
    """
    doc = FreeCAD.newDocument("ContainerTest10")
    try:
        master = _build_master(doc)
        ref = create_config_ref(doc, master.sheet, "TypeA", name="ConfigRefA")
        box = doc.addObject("Part::Box", "Box")
        box.setExpression("Length", "<<ConfigRefA>>.Length * 1mm")
        doc.recompute()
        assert abs(box.Length.Value - 80) < 1e-9

        ref.Label = "Settings"
        box.setExpression("Length", "ConfigRefA.Length * 1mm")
        doc.recompute()
        assert abs(box.Length.Value - 80) < 1e-9, box.Length

        box.setExpression("Length", "<<Settings>>.Length * 1mm")
        doc.recompute()
        assert abs(box.Length.Value - 80) < 1e-9, box.Length
    finally:
        FreeCAD.closeDocument("ContainerTest10")


def test_command_uses_active_container():
    """Creating a ConfigRef while a container is active puts it in there.

    This is FreeCAD's convention (the same active objects the core commands
    use): new objects belong to the active PartDesign Body or Part container.
    """
    from freecad.spreadsheetplus.commands.create_config_ref import active_container

    doc = FreeCAD.newDocument("ContainerTest11")
    try:
        master = _build_master(doc)
        body = doc.addObject("PartDesign::Body", "Body")
        part = doc.addObject("App::Part", "Part")
        doc.recompute()
        view = Gui.ActiveDocument.ActiveView

        def run_command():
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(master.sheet)
            before = {o.Name for o in doc.Objects}
            Gui.runCommand("SpreadSheetPlus_CreateConfigRef")
            doc.recompute()
            created = [o for o in doc.Objects if o.Name not in before]
            assert len(created) == 1, [o.Name for o in created]
            return created[0]

        # no active container -> document root
        view.setActiveObject("pdbody", None)
        view.setActiveObject("part", None)
        assert active_container(doc) is None
        assert run_command() not in body.Group

        # active Body
        view.setActiveObject("pdbody", body)
        assert active_container(doc) is body
        ref = run_command()
        assert ref in body.Group, [o.Name for o in body.Group]
        assert body.BaseFeature in (None, ref) or body.BaseFeature.Name != ref.Name
        assert ref.Length == 80

        # active Part
        view.setActiveObject("pdbody", None)
        view.setActiveObject("part", part)
        assert active_container(doc) is part
        ref2 = run_command()
        assert ref2 in part.Group, [o.Name for o in part.Group]

        # clean up the active objects so later tests start from a clean slate
        view.setActiveObject("pdbody", None)
        view.setActiveObject("part", None)
    finally:
        save_document(doc, "container_active_command")
        FreeCAD.closeDocument("ContainerTest11")


def main():
    tests = [
        value
        for key, value in sorted(globals().items())
        if key.startswith("test_") and callable(value)
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}", flush=True)
        except Exception:  # noqa: BLE001 - report and continue
            failures += 1
            print(f"FAIL {test.__name__}", flush=True)
            traceback.print_exc()

    print(f"{len(tests) - failures}/{len(tests)} tests passed", flush=True)
    sys.stdout.flush()

    mw = Gui.getMainWindow()
    if mw is not None:
        mw.close()

    sys.exit(1 if failures else 0)


# NOTE: FreeCAD executes scripts with __name__ set to the script's basename
# (not "__main__"), so main() is called unconditionally.
main()
