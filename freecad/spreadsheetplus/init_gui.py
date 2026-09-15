# SPDX-License-Identifier: LGPL-2.1-or-later
"""
GUI entry point for the spreadsheetplus addon.

This file is imported by FreeCAD after ``__init__.py`` when the GUI is
available. It is the place for GUI-related initialization: registering
workbenches, toolbars, menus, and loading icons/translations.

FreeCAD loading sequence:
    1. freecad.spreadsheetplus.__init__ (headless, always runs)
    2. freecad.spreadsheetplus.init_gui (GUI only)

Keep this file fast - it runs on every FreeCAD GUI startup.
"""

from .resources import Resources
from .commands import (
    CreateMasterSheet,
    CreateConfigRef,
    SwitchConfiguration,
)
from .workbench import SpreadSheetPlusWorkbench

# Install icons
Resources.gui_register_icons()

# Install translations (if any)
Resources.gui_register_translations()

# Install commands
for command in (
    CreateMasterSheet,
    CreateConfigRef,
    SwitchConfiguration,
):
    command.Install()

# Register the workbench
SpreadSheetPlusWorkbench.Install()
