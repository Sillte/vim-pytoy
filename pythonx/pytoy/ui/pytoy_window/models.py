from enum import StrEnum

class ViewportMoveMode(StrEnum):
    """When Cursor/Selection is changed,
    this specifies how the viewport of the window changes.
    """
    NONE = "none"
    ENSURE_VISIBLE = "ensure_visibile"
    CENTER = "center"
    TOP = "top"