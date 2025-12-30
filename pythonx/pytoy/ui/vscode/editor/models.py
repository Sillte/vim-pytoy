from enum import IntEnum


class TextEditorRevealType(IntEnum):
    Default = 0
    InCenter = 1
    InCenterIfOutsideViewport = 2
    AtTop = 3
