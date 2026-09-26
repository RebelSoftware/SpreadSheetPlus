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
from freecad.spreadsheetplus.config_ref import row_selector, switch_configuration
from freecad.spreadsheetplus.master_sheet import MasterSheet
from freecad.spreadsheetplus.variants import attach as attach_variants
from freecad.spreadsheetplus.variants import variant_links
from fcsp_test_support import TEST_DOCUMENTS_DIR, save_document

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


def _close(doc):
    if doc is not None:
        try:
            FreeCAD.closeDocument(doc.Name)
        except Exception:
            pass


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


def test_part_selector_offers_the_available_configurations():
    doc = FreeCAD.newDocument("VariantEum")
    try:
        body, shank, head, box = _bolt(doc)

        # The part's selector is an enumeration of the master's rows, so the
        # property editor offers them as a drop-down: a Body is a C++ object and
        # only a Python object can open the ConfigRef's own picker dialog.
        assert body.getTypeIdOfProperty("BoltLength") == "App::PropertyEnumeration"
        assert body.getEnumerationsOfProperty("BoltLength") == ["long", "short"]
        assert body.getEnumerationsOfProperty("HeadStyle") == ["button", "flanged"]
        assert body.BoltLength == "short"

        # ...while the reference's own Configuration stays a plain string: it is
        # the read-through selection, and scripts and expressions may set it.
        assert shank.getTypeIdOfProperty("Configuration") == "App::PropertyString"

        # picking a row on the part (what the drop-down does) drives the part
        body.BoltLength = "long"
        doc.recompute()
        assert shank.Configuration == "long"
        assert shank.Length == 50
        assert box.Length.Value == 50
    finally:
        save_document(doc, "variants_selector_enum")
        FreeCAD.closeDocument("VariantEum")


def test_part_selector_follows_the_masters_configurations():
    doc = FreeCAD.newDocument("VariantRows")
    try:
        body, shank, head, box = _bolt(doc)
        master = MasterSheet(shank.Master)
        assert body.getEnumerationsOfProperty("BoltLength") == ["long", "short"]

        # a row added to the master shows up in the selector
        master.add_configuration("medium")
        doc.recompute()
        assert body.getEnumerationsOfProperty("BoltLength") == [
            "long",
            "medium",
            "short",
        ]

        # ...and is dropped again once the master no longer has it
        master.remove_configuration("medium")
        doc.recompute()
        assert body.getEnumerationsOfProperty("BoltLength") == ["long", "short"]
    finally:
        save_document(doc, "variants_selector_rows")
        FreeCAD.closeDocument("VariantRows")


def test_selector_keeps_a_row_the_master_no_longer_has():
    doc = FreeCAD.newDocument("VariantStale")
    try:
        body, shank, head, box = _bolt(doc)
        master = MasterSheet(shank.Master)
        switch_configuration(shank, "long")
        doc.recompute()
        assert body.BoltLength == "long"

        master.remove_configuration("long")
        doc.recompute()

        # An enumeration can only hold one of its own items, so the row the
        # master no longer has is kept as an extra item: the selector must not
        # silently jump to another row (and so change the part).
        assert body.BoltLength == "long"
        assert body.getEnumerationsOfProperty("BoltLength") == ["short", "long"]
        assert shank.Configuration == "long"
        assert shank.ConfigurationValid is False
        assert "long" in shank.ConfigurationError

        # picking a row that does exist drops the stale item again
        switch_configuration(shank, "short")
        doc.recompute()
        assert body.getEnumerationsOfProperty("BoltLength") == ["short"]
        assert body.BoltLength == "short"
        assert shank.ConfigurationValid is True
    finally:
        save_document(doc, "variants_selector_stale")
        FreeCAD.closeDocument("VariantStale")


def test_a_part_side_switch_never_creates_a_variant():
    """The copy-on-change contract, pinned - see PLAN.md decision 6.

    FreeCAD turns a link into an independent variant when one of the link's
    *own* mirrored properties changes. A change on the part (what the ConfigRef's
    picker, the *Switch configuration* command and the part's own drop-down
    write) is synced into that mirror instead, so it updates every link that
    still follows the part and creates nothing. `variant_links()` is what tells
    the picker which links such a change just reached.
    """
    doc = FreeCAD.newDocument("VariantContract")
    try:
        body, shank, head, box = _bolt(doc)
        link = doc.addObject("App::Link", "Bolt1")
        link.LinkedObject = body
        link.LinkCopyOnChange = "Enabled"
        doc.recompute()

        # the part's selector is what a switch writes, and this link follows it
        assert row_selector(shank) == (body, "BoltLength")
        assert variant_links(body, "BoltLength") == [link]
        assert variant_links(body, "NoSuchRow") == []

        switch_configuration(shank, "long")
        doc.recompute()
        assert link.LinkedObject is body  # no variant...
        assert link.BoltLength == "long"  # ...the link followed the part
        assert shank.Configuration == "long"

        # the link's own row is what makes it diverge into a variant
        link.BoltLength = "short"
        doc.recompute()
        assert link.LinkedObject is not body
        assert link.LinkedObject.BoltLength == "short"
        assert body.BoltLength == "long"  # the part keeps its row
        assert shank.Configuration == "long"
        assert shank.Length == 50

        # a link that diverged no longer follows the part, so a part-side switch
        # has nothing to report about it
        assert variant_links(body, "BoltLength") == []
    finally:
        save_document(doc, "variants_contract")
        FreeCAD.closeDocument("VariantContract")


def test_switch_configuration_keeps_an_unknown_row_selectable():
    doc = FreeCAD.newDocument("VariantUnknown")
    try:
        body, shank, head, box = _bolt(doc)

        # An enumeration raises for a value that is not one of its items, so a
        # row that is not in the master's table (a script typo, or a renamed
        # row) is added to the selector rather than raising or being ignored.
        switch_configuration(shank, "not-a-row")
        doc.recompute()

        assert body.BoltLength == "not-a-row"
        assert shank.Configuration == "not-a-row"
        assert shank.ConfigurationValid is False
        assert "not-a-row" in shank.ConfigurationError
        assert "not-a-row" in body.getEnumerationsOfProperty("BoltLength")
    finally:
        save_document(doc, "variants_selector_unknown")
        FreeCAD.closeDocument("VariantUnknown")


def test_legacy_string_selector_is_upgraded():
    doc = FreeCAD.newDocument("VariantLegacy")
    try:
        lengths = _master(doc, "Lengths", "Length", {"short": 20, "long": 50})
        body = doc.addObject("PartDesign::Body", "Bolt")
        ref = create_config_ref(doc, lengths.sheet, "short", name="BoltLength")
        body.addObject(ref)
        doc.recompute()
        assert body.getTypeIdOfProperty("BoltLength") == "App::PropertyEnumeration"

        # pretend the document was written by a version that used a plain string
        body.removeProperty("BoltLength")
        body.addProperty("App::PropertyString", "BoltLength", "ConfigRef", "")
        body.setPropertyStatus("BoltLength", "CopyOnChange")
        body.BoltLength = "long"
        doc.recompute()

        # the selector is rebuilt as an enumeration, keeping the row it selected
        assert body.getTypeIdOfProperty("BoltLength") == "App::PropertyEnumeration"
        assert body.getEnumerationsOfProperty("BoltLength") == ["long", "short"]
        assert "CopyOnChange" in body.getPropertyStatus("BoltLength")
        assert body.BoltLength == "long"
        assert ref.Configuration == "long"
        assert ref.Length == 50
    finally:
        save_document(doc, "variants_selector_legacy")
        FreeCAD.closeDocument("VariantLegacy")


def test_selectors_and_variants_survive_a_reopen():
    TEST_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = str(TEST_DOCUMENTS_DIR / "variants_selector_reopen.FCStd")

    doc = FreeCAD.newDocument("VariantReopen")
    reopened = None
    try:
        body, shank, head, box = _bolt(doc)
        link = doc.addObject("App::Link", "Bolt1")
        link.LinkedObject = body
        link.LinkCopyOnChange = "Enabled"
        doc.recompute()
        link.BoltLength = "long"
        doc.recompute()

        doc.saveAs(path)
        _close(doc)
        doc = None

        reopened = FreeCAD.openDocument(path)
        reopened.recompute()

        body2 = reopened.getObject("Bolt")
        ref2 = reopened.getObject("BoltLength")
        assert isinstance(ref2.Proxy, ConfigRef)  # the proxy came back
        assert body2.getTypeIdOfProperty("BoltLength") == "App::PropertyEnumeration"
        assert body2.getEnumerationsOfProperty("BoltLength") == ["long", "short"]
        assert body2.BoltLength == "short"
        assert ref2.Configuration == "short"
        assert ref2.Length == 20

        # the variant kept its own row, and can still switch
        variant = reopened.getObject("Bolt1")
        assert variant.BoltLength == "long"
        variant.HeadStyle = "flanged"
        reopened.recompute()
        assert variant.HeadStyle == "flanged"
    finally:
        _close(doc)
        _close(reopened)


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
        assert row_selector(ref) == (ref, "Configuration")
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
