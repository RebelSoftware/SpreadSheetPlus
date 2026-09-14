# Translations

Compiled Qt translation files (`.qm`) live in this folder. They are registered
at startup by `Resources.gui_register_translations()`
(`Gui.addLanguagePath()` + `Gui.updateLocale()`), which loads `*_<lang>.qm` for
the active FreeCAD language.

## Files

- `SpreadSheetPlus_de.ts` — German source translation (XML, editable).
- `SpreadSheetPlus_de.qm` — compiled German translation (shipped with the addon).

Qt only loads the **compiled** `.qm` at runtime — edit the `.ts` and recompile.

## Adding or updating a language

1. Copy `SpreadSheetPlus_de.ts` to `SpreadSheetPlus_<lang>.ts`
   (e.g. `_fr`, `_es`; use the two-letter top-level domain FreeCAD expects).
2. Translate the `<translation>` elements (leave `<source>` unchanged).
3. Compile it with Qt's `lrelease` (e.g. `usr/lib/qt6/bin/lrelease` inside a
   FreeCAD AppImage):

   ```bash
   lrelease SpreadSheetPlus_fr.ts -qm SpreadSheetPlus_fr.qm
   ```

4. Restart FreeCAD with that language selected (`Edit → Preferences → General →
   Language`) — the strings come from the `.qm` automatically.

> Strings are wrapped with `translate("SpreadSheetPlus", "...")` in the code
> (context `SpreadSheetPlus`), so the `.ts` context name must stay
> `SpreadSheetPlus`. See also FreeCAD's "Translating an external workbench"
> guide: https://wiki.freecad.org/Translating_an_external_workbench
