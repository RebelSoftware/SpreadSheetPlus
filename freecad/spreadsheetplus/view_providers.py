# SPDX-License-Identifier: LGPL-2.1-or-later
"""ViewProviders for SpreadSheetPlus objects."""

from __future__ import annotations

from .resources import Resources


class ConfigRefViewProvider:
    """ViewProvider for the ConfigRef object (tree icon).

    Attached to whatever object type the ConfigRef uses (`Part::Part2DObjectPython`
    for new references, `App::FeaturePython` for pre-0.2 ones).

    The tree icon doubles as a validity signal: a reference whose configuration
    does not resolve, or whose master table has structural problems, is shown
    with a warning icon instead of the normal one. `ConfigRef._refresh_icon`
    calls `signalChangeIcon()` when that state changes.
    """

    def __init__(self, vobj) -> None:
        vobj.Proxy = self
        self.Object = vobj.Object

    def getIcon(self) -> str:
        if _problems(self.Object):
            return Resources.icon("spreadsheetplus-config-warning.svg")
        return Resources.icon("spreadsheetplus-config.svg")

    def attach(self, vobj) -> None:
        self.Object = vobj.Object

    def claimChildren(self):
        return []

    def onDelete(self, feature, subelements) -> bool:
        return True

    def __getstate__(self):
        return None

    def __setstate__(self, state) -> None:
        return None


def _problems(obj) -> list[str]:
    """Status messages reported by *obj* (empty means everything is fine)."""
    if obj is None:
        return []
    messages = []
    try:
        if not obj.ConfigurationValid and obj.ConfigurationError:
            messages.append(obj.ConfigurationError)
        if not obj.TableValid and obj.TableErrors:
            messages.append(obj.TableErrors)
    except Exception:
        # The object is not a (fully initialised) ConfigRef; no warning then.
        return []
    return messages
