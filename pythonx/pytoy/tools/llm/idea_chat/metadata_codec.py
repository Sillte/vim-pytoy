from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Self

import yamlrocks
from pytoy_llm.idea.note import IdeaNote

from pytoy.shared.lib.text import LineRange, ReplaceLinesPatch


@dataclass(frozen=True)
class BufferMetadataCodec:
    _FRONT_MATTER_MARKER: ClassVar[str] = "---"
    title: str | None = None

    @classmethod
    def from_dashboard(cls, dashboard_path: Path) -> Self:
        if not dashboard_path.exists():
            return cls()
        metadata = IdeaNote.from_path(dashboard_path, root=dashboard_path.parent).metadata
        title = metadata["title"] if "title" in metadata.keys() else None
        return cls(title=title)

    def _content_text(self) -> str:
        metadata = {"title": self.title}
        yaml_text = yamlrocks.dumps(metadata).decode().strip("\r\n")
        if self.title is None:
            yaml_text = "title: null"
        return f"{self._FRONT_MATTER_MARKER}\n{yaml_text}\n{self._FRONT_MATTER_MARKER}\n"

    def create_patch(self, buffer_content: str) -> ReplaceLinesPatch:
        lines = buffer_content.splitlines()
        for i, line in enumerate(lines):
            if line.strip(" \t"):
                start = i
                break
        else:
            start = len(lines)
        lines = lines[start:]

        if lines and lines[0].strip(" \t") == self._FRONT_MATTER_MARKER:
            try:
                end = next(
                    index for index, line in enumerate(lines[1:], 1) if line.strip(" \t") == self._FRONT_MATTER_MARKER
                )
            except StopIteration:
                end = -1
            if end >= 0:
                return ReplaceLinesPatch(LineRange(start=start, end=start + end + 1), self._content_text().splitlines())
        return ReplaceLinesPatch(LineRange(start=0, end=start), self._content_text().splitlines())
