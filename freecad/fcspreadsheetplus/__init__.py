# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Entry point for the fcspreadsheetplus addon (headless mode).

This file is loaded once during FreeCAD initialization when the addon is not
disabled. It runs in headless mode, so no Gui imports or calls are allowed here.

FreeCAD discovers addons using the native namespace package structure::

    freecad/fcspreadsheetplus/

The parent ``freecad`` package uses native namespace packaging (no
``__init__.py``), allowing multiple addons to coexist under the same namespace.

Keep this file fast - it runs on every FreeCAD startup.
"""

from .version import __version__  # noqa: F401
