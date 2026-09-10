# SPDX-License-Identifier: LGPL-2.1-or-later
"""Resource manager: icons and translations for the addon.

Uses importlib.resources for path resolution so the addon works both from a
regular install and from a zip import.
"""

from __future__ import annotations

import importlib.resources
from typing import ClassVar

import FreeCAD as App

try:
    from importlib.resources.abc import Traversable
except ImportError:  # Python < 3.11 fallback
    from importlib.abc import Traversable


class Resources:
    """Addon resource manager."""

    _pkg: ClassVar[Traversable] = importlib.resources.files(__name__)
    _gui_icons_added: ClassVar[bool] = False
    _gui_translations_added: ClassVar[bool] = False

    @classmethod
    def icon(cls, path: str) -> str:
        """Resolve an icon filename to its absolute path."""
        base = cls._pkg / "icons"
        return str(base.joinpath(path))

    @classmethod
    def __truediv__(cls, path: str) -> str:
        """Resolve a relative resource path to its absolute path."""
        return str(cls._pkg.joinpath(path))

    @classmethod
    def gui_register_icons(cls) -> bool:
        if not App.GuiUp:
            raise RuntimeError(f"{__name__}: Icon path cannot be added without Gui.")
        if cls._gui_icons_added:
            return False
        icons = str(cls._pkg / "icons")
        App.Console.PrintLog(f"Installing {__name__}: icons={icons}\n")
        App.Gui.addIconPath(icons)
        cls._gui_icons_added = True
        return True

    @classmethod
    def gui_register_translations(cls) -> bool:
        if not App.GuiUp:
            raise RuntimeError(f"{__name__}: Translations path cannot be added without Gui.")
        if cls._gui_translations_added:
            return False
        translations = str(cls._pkg / "translations")
        App.Console.PrintLog(f"Installing {__name__}: translations={translations}\n")
        App.Gui.addLanguagePath(translations)
        App.Gui.updateLocale()
        cls._gui_translations_added = True
        return True
