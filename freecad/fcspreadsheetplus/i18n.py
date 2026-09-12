# SPDX-License-Identifier: LGPL-2.1-or-later
"""Translation helpers for FCSpreadSheetPlus.

Every user-facing string is wrapped in ``translate("FCSpreadSheetPlus", ...)``.
At runtime Qt looks the text up in any installed translator; the compiled
``.qm`` files live in ``resources/translations/`` and are registered by
``Resources.gui_register_translations()`` (see ``docs/translations.md``).
"""

from __future__ import annotations

from PySide6 import QtCore


def translate(context: str, text: str, disambig: str | None = None) -> str:
    """Return the translation of *text* for *context*, or *text* if untranslated."""
    return QtCore.QCoreApplication.translate(context, text, disambig)
