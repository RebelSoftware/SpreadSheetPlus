# Translations

Compiled Qt translation files (`.qm`) live in this folder. They are registered
at startup by `Resources.gui_register_translations()`
(`Gui.addLanguagePath()` + `Gui.updateLocale()`), which loads `*_<lang>.qm` for
the active FreeCAD language.

## Files

- `FCSpreadSheetPlus_de.ts` — German source translation (XML, editable).
- `FCSpreadSheetPlus_de.qm` — compiled German translation (shipped with the addon).

Qt only loads the **compiled** `.qm` at runtime — edit the `.ts` and recompile.

## Adding or updating a language

1. Copy `FCSpreadSheetPlus_de.ts` to `FCSpreadSheetPlus_<lang>.ts`
   (e.g. `_fr`, `_es`; use the two-letter top-level domain FreeCAD expects).
2. Translate the `<translation>` elements (leave `<source>` unchanged).
3. Compile it with Qt's `lrelease` (bundled with FreeCAD at
   `usr/lib/qt6/bin/lrelease` inside the AppImage):

   ```bash
   ~/Applications/squashfs-root/usr/lib/qt6/bin/lrelease \
       FCSpreadSheetPlus_fr.ts -qm FCSpreadSheetPlus_fr.qm
   ```

4. Restart FreeCAD with that language selected (`Edit → Preferences → General →
   Language`) — the strings come from the `.qm` automatically.

> Strings are wrapped with `translate("FCSpreadSheetPlus", "...")` in the code
> (context `FCSpreadSheetPlus`), so the `.ts` context name must stay
> `FCSpreadSheetPlus`. See also FreeCAD's "Translating an external workbench"
> guide: https://wiki.freecad.org/Translating_an_external_workbench
