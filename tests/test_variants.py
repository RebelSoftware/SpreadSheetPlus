"""Part variant tests (App::Link "Copy on change") - Phase 4, step 10.

A part is configured through its container: every ConfigRef inside a Body gets
its own selector property on that Body, so a link with copy-on-change gives each
variant its own row for every configuration - the "configure the part" model,
rather than one combinatorial row per variant.

Run inside FreeCAD's interpreter:

    freecadcmd -M <repo-root> tests/test_variants.py
"""

import sys
import traceback

import FreeCAD

from freecad.spreadsheetplus.config_ref import ConfigRef
from freecad.spreadsheetplus.config_ref import create as create_config_ref
from freecad.spreadsheetplus.config_ref import switch_configuration
from freecad.spreadsheetplus.master_sheet import MasterSheet
from freecad.spreadsheetplus.variants import attach as attach_variants
from fcsp_test_support import save_document

# The package attaches the observer on import; be explicit about the dependency.
attach_variants()


def _master(doc, name, param, rows):
    master = MasterSheet.create(doc, name=name)
    master.add_parameter(param)
    for row, value in rows.items():
        master.add_configuration(row)
        master.set_value(row, param, value)
    return master


def _bolt(doc):
    """A part configured by two independent masters (length and head style)."""
    lengths = _master(doc, "Lengths", "Length", {"short": 20, "long": 50})
    heads = _master(doc, "Heads", "Diameter", {"button": 8, "flanged": 14})

    body = doc.addObject("PartDesign::Body", "Bolt")
    shank = create_config_ref(doc, lengths.sheet, "short", name="BoltLength")
    head = create_config_ref(doc, heads.sheet, "button", name="HeadStyle")
    body.addObject(shank)
    body.addObject(head)

    box = body.newObject("PartDesign::AdditiveBox", "Shank")
    box.setExpression("Length", "BoltLength.Length * 1mm")
    box.setExpression("Width", "HeadStyle.Diameter * 1mm")
    doc.recompute()
    return body, shank, head, box


def _config_refs(obj):
    return {
        child.ConfigurationName: child
        for child in obj.Group
        if isinstance(getattr(child, "Proxy", None), ConfigRef)
    }


def test_part_carries_one_selector_per_configuration():
    doc = FreeCAD.newDocument("VariantSlots")
    try:
        body, shank, head, box = _bolt(doc)

        # one selector property per configuration, on the part itself
        assert shank.ConfigurationName == "BoltLength"
        assert head.ConfigurationName == "HeadStyle"
        assert body.getGroupOfProperty("BoltLength") == "ConfigRef"
        assert body.getGroupOfProperty("HeadStyle") == "ConfigRef"
        assert "CopyOnChange" in body.getPropertyStatus("BoltLength")
        assert "CopyOnChange" in body.getPropertyStatus("HeadStyle")
        assert body.BoltLength == "short"
        assert body.HeadStyle == "button"

        # ...and each ConfigRef reads its row back from it
        assert shank.Configuration == "short"
        assert head.Configuration == "button"
        assert shank.Length == 20
        assert head.Diameter == 8
        assert box.Length.Value == 20
        assert box.Width.Value == 8

        # the ConfigRef follows the part's selector, and stays writable so the
        # Switch configuration command keeps working
        assert body.BoltLength == shank.Configuration
        assert body.HeadStyle == head.Configuration
        assert "ReadOnly" not in shank.getEditorMode("Configuration")
    finally:
        save_document(doc, "variants_slots")
        FreeCAD.closeDocument("VariantSlots")


def test_config_ref_row_pushes_up_to_the_part():
    doc = FreeCAD.newDocument("VariantPush")
    try:
        body, shank, head, box = _bolt(doc)

        # changing the row on the ConfigRef (the pre-variant workflow) reaches
        # the part, so its links and future variants follow
        shank.Configuration = "long"
        doc.recompute()
        assert body.BoltLength == "long"
        assert box.Length.Value == 50
        assert head.Configuration == "button"
    finally:
        save_document(doc, "variants_push")
        FreeCAD.closeDocument("VariantPush")


def test_part_selector_drives_the_configuration():
    doc = FreeCAD.newDocument("VariantSelect")
    try:
        body, shank, head, box = _bolt(doc)

        switch_configuration(shank, "long")
        switch_configuration(head, "flanged")
        doc.recompute()

        assert body.BoltLength == "long"
        assert body.HeadStyle == "flanged"
        assert shank.Configuration == "long"
        assert shank.Length == 50
        assert box.Length.Value == 50
        assert box.Width.Value == 14
    finally:
        save_document(doc, "variants_select")
        FreeCAD.closeDocument("VariantSelect")


def test_link_variant_picks_its_own_rows():
    doc = FreeCAD.newDocument("VariantLink")
    try:
        body, shank, head, box = _bolt(doc)

        link = doc.addObject("App::Link", "Bolt1")
        link.LinkedObject = body
        link.LinkCopyOnChange = "Enabled"
        doc.recompute()

        # every configuration is mirrored on the link...
        assert link.getGroupOfProperty("BoltLength") == "Configuration (ConfigRef)"
        assert link.getGroupOfProperty("HeadStyle") == "Configuration (ConfigRef)"

        # ...and changing any one of them turns the link into an independent copy
        link.BoltLength = "long"
        doc.recompute()
        copy = link.LinkedObject
        assert copy is not body
        assert copy.BoltLength == "long"
        assert copy.HeadStyle == "button"  # the other selection came along

        copied = _config_refs(copy)
        assert set(copied) == {"BoltLength", "HeadStyle"}
        assert copied["BoltLength"].Configuration == "long"
        assert copied["HeadStyle"].Configuration == "button"
        assert copied["BoltLength"].Length == 50
        assert copied["HeadStyle"].Diameter == 8

        # a later change on the *other* configuration updates the same copy
        link.HeadStyle = "flanged"
        doc.recompute()
        assert link.LinkedObject is copy
        assert copy.HeadStyle == "flanged"
        assert copied["HeadStyle"].Configuration == "flanged"
        assert copied["HeadStyle"].Diameter == 14

        # the template keeps its own selections throughout
        assert body.BoltLength == "short"
        assert body.HeadStyle == "button"
        assert shank.Configuration == "short"
        assert head.Configuration == "button"
        assert box.Length.Value == 20
        assert box.Width.Value == 8
    finally:
        save_document(doc, "variants_link")
        FreeCAD.closeDocument("VariantLink")


def test_stale_selectors_are_removed():
    doc = FreeCAD.newDocument("VariantCleanup")
    try:
        body, shank, head, box = _bolt(doc)
        assert sorted(body._ConfigurationSlots) == ["BoltLength", "HeadStyle"], list(
            body._ConfigurationSlots
        )

        box.setExpression("Width", None)
        doc.removeObject("HeadStyle")
        shank.touch()
        doc.recompute()

        assert not hasattr(body, "HeadStyle")
        assert list(body._ConfigurationSlots) == ["BoltLength"]
        assert body.BoltLength == "short"
        assert shank.Length == 20
    finally:
        save_document(doc, "variants_cleanup")
        FreeCAD.closeDocument("VariantCleanup")


def test_root_config_ref_keeps_its_own_selector():
    doc = FreeCAD.newDocument("VariantRoot")
    try:
        lengths = _master(doc, "Lengths", "Length", {"short": 20, "long": 50})
        ref = create_config_ref(doc, lengths.sheet, "short", name="BoltLength")
        doc.recompute()

        # outside a container the ConfigRef itself is the selector
        assert ref.Configuration == "short"
        assert "ReadOnly" not in ref.getEditorMode("Configuration")
        assert "CopyOnChange" in ref.getPropertyStatus("Configuration")

        link = doc.addObject("App::Link", "Link")
        link.LinkedObject = ref
        link.LinkCopyOnChange = "Enabled"
        doc.recompute()
        assert link.getGroupOfProperty("Configuration") == "Configuration (ConfigRef)"

        link.Configuration = "long"
        doc.recompute()
        assert link.LinkedObject is not ref
        assert link.Length == 50
        assert ref.Configuration == "short"
        assert ref.Length == 20
    finally:
        save_document(doc, "variants_root")
        FreeCAD.closeDocument("VariantRoot")


def test_selector_name_clash_with_a_property_is_reported():
    doc = FreeCAD.newDocument("VariantClash")
    try:
        lengths = _master(doc, "Lengths", "Length", {"short": 20, "long": 50})
        body = doc.addObject("PartDesign::Body", "Bolt")
        ref = create_config_ref(doc, lengths.sheet, "short", name="BoltLength")
        body.addObject(ref)
        ref.ConfigurationName = "Shape"  # the Body already has a Shape property
        doc.recompute()

        assert ref.ConfigurationValid is False
        assert "Shape" in ref.ConfigurationError
        # it still works from its own value, and stays editable
        assert ref.Configuration == "short"
        assert ref.Length == 20
        assert "ReadOnly" not in ref.getEditorMode("Configuration")
        assert "Shape" not in list(body._ConfigurationSlots)
    finally:
        save_document(doc, "variants_clash")
        FreeCAD.closeDocument("VariantClash")


def test_selector_name_clash_between_config_refs_is_reported():
    doc = FreeCAD.newDocument("VariantClash2")
    try:
        lengths = _master(doc, "Lengths", "Length", {"short": 20, "long": 50})
        heads = _master(doc, "Heads", "Diameter", {"button": 8, "flanged": 14})

        body = doc.addObject("PartDesign::Body", "Bolt")
        first = create_config_ref(doc, lengths.sheet, "short", name="ConfigA")
        second = create_config_ref(doc, heads.sheet, "button", name="ConfigB")
        body.addObject(first)
        body.addObject(second)
        first.ConfigurationName = "Same"
        second.ConfigurationName = "Same"
        doc.recompute()

        for ref in (first, second):
            assert ref.ConfigurationValid is False
            assert "more than one ConfigRef" in ref.ConfigurationError
            assert ref.Configuration
        assert not hasattr(body, "Same")
    finally:
        save_document(doc, "variants_clash2")
        FreeCAD.closeDocument("VariantClash2")


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
    sys.exit(1 if failures else 0)


# NOTE: FreeCADCmd executes scripts with __name__ set to the script's basename
# (not "__main__"), so main() is called unconditionally.
main()
