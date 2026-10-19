from dataclasses import dataclass
from typing import Any, ClassVar, Self

import yamlrocks
from pytoy_llm.idea.note import IdeaNote  # noqa
from pytoy_llm.models import LLMParam, LLMTokens, UsageLimit  # noqa

from pytoy.shared.lib.text import LineRange, ReplaceLinesPatch

from .statuses import IdeaCirculationStatus


@dataclass(frozen=True)
class BufferMetadataCodec:
    _FRONT_MATTER_MARKER: ClassVar[str] = "---"
    status: IdeaCirculationStatus

    @classmethod
    def from_any(cls, status: IdeaCirculationStatus) -> Self:
        return cls(status=status)

    def _content_text(self) -> str:
        metadata: dict[str, Any] = {"kind": self.status.kind}
        if workspace_name := self.status.workspace_name:
            metadata["workspace_name"] = workspace_name
        metadata["value_cycle_execution_policy"] = self.status.value_cycle_execution_policy
        if self.status.value_cycle_working_status:
            metadata["value_cycle_working_status"] = self.status.value_cycle_working_status
        if self.status.value_cycle_message is not None:
            metadata["value_cycle_message"] = self.status.value_cycle_message
        if self.status.llm_tokens:
            metadata["llm_tokens"] = self.status.llm_tokens.model_dump(exclude_none=True)
        yaml_text = yamlrocks.dumps(metadata).decode().strip("\r\n")
        return f"{self._FRONT_MATTER_MARKER}\n{yaml_text}\n{self._FRONT_MATTER_MARKER}\n"

    @classmethod
    def get_metadata_line_range(cls, buffer_content: str) -> LineRange | None:
        lines = buffer_content.splitlines()
        for i, line in enumerate(lines):
            if line.strip(" \t"):
                start = i
                break
        else:
            start = len(lines)
        lines = lines[start:]

        if lines and lines[0].strip(" \t") == cls._FRONT_MATTER_MARKER:
            try:
                end = next(
                    index for index, line in enumerate(lines[1:], 1) if line.strip(" \t") == cls._FRONT_MATTER_MARKER
                )
            except StopIteration:
                end = -1
            if end >= 0:
                return LineRange(start=start, end=start + end + 1)
        return None

    def create_patch(self, buffer_content: str) -> ReplaceLinesPatch:
        line_range = self.get_metadata_line_range(buffer_content)
        if line_range:
            return ReplaceLinesPatch(line_range, self._content_text().splitlines())

        lines = buffer_content.splitlines()
        for i, line in enumerate(lines):
            if line.strip(" \t"):
                start = i
                break
        else:
            start = len(lines)
        return ReplaceLinesPatch(LineRange(start=0, end=start), self._content_text().splitlines())
