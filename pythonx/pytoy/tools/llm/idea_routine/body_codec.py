from dataclasses import dataclass
from typing import ClassVar, Self

from pytoy_llm.idea import IdeaNote, IdeaSpace  # noqa

from pytoy.shared.lib.text import LineRange, ReplaceLinesPatch

from .metadata_codec import BufferMetadataCodec


@dataclass(frozen=True)
class BufferBodyCodec:
    _FRONT_MATTER_MARKER: ClassVar[str] = "---"
    idea_space: IdeaSpace

    @classmethod
    def from_any(cls, idea_space: IdeaSpace) -> Self:
        return cls(idea_space=idea_space)

    def to_text(self) -> str:
        elements = []
        dashboard_path = self.idea_space.folder_path / "dashboard.md"
        if dashboard_path.exists():
            elements.append("## Dashboard\n\n `dashboard.md`")
        else:
            elements.append("No Dashboard")

        master_folder = self.idea_space.folder_path / "master"
        paths = list(master_folder.glob("**/*.md"))
        if paths:
            text = "## User Intentions\n\n"
            text += "\n".join(f"`{path.relative_to(self.idea_space.folder_path)}`" for path in paths)
            elements.append(text)
        else:
            elements.append("No user intentions in `master` folder. Plemase make a `IdeaNote`.")

        return "\n\n".join(elements)

    def create_patch(self, buffer_content: str) -> ReplaceLinesPatch:
        metadata_line_range = BufferMetadataCodec.get_metadata_line_range(buffer_content)
        if metadata_line_range:
            line_range = LineRange(metadata_line_range.end, len(buffer_content.splitlines()))
            return ReplaceLinesPatch(line_range, self.to_text().splitlines())
        else:
            line_range = LineRange(0, len(buffer_content.splitlines()))
            return ReplaceLinesPatch(line_range, self.to_text().splitlines())
