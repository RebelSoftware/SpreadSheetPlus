"""Shared helpers for FCSpreadSheetPlus test scripts.

Tests save their FreeCAD documents into the git-ignored ``test_documents/``
folder so the results can be opened and reviewed visually after a run.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_DOCUMENTS_DIR = ROOT / "test_documents"


def save_document(doc, name=None):
    """Save a FreeCAD document into ``test_documents/``.

    Returns the written path (or None if *doc* is None). The folder is created
    if missing.
    """
    if doc is None:
        return None
    TEST_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = TEST_DOCUMENTS_DIR / f"{name or doc.Name}.FCStd"
    doc.saveAs(str(path))
    print(f"Saved test document: {path}", flush=True)
    return path
