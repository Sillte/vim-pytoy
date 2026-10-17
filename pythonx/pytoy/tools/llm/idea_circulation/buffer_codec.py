from dataclasses import dataclass
from typing import ClassVar, Self

from pytoy.shared.lib.text import LineRange, NoReplacePatch, ReplaceLinesPatch


@dataclass(frozen=True)
class LLMBufferCodec:
    _LLM_MESSAGES_SEPARATOR_START: ClassVar[str] = "---LLMMessages-BEGIN---"
    _LLM_MESSAGES_SEPARATOR_END: ClassVar[str] = "---LLMMessages-END---"
    messages_domain: str

    @classmethod
    def from_llm_buffer(cls, buffer_content: str) -> Self:
        lines = buffer_content.split("\n")
        index = 0
        start_separator_index = None
        end_separator_index = None
        while index < len(lines):
            if cls._LLM_MESSAGES_SEPARATOR_START == lines[index].strip(" \t"):
                start_separator_index = index
                while index < len(lines):
                    if cls._LLM_MESSAGES_SEPARATOR_END == lines[index].strip(" \t"):
                        end_separator_index = index
                        break
                    index += 1
                break
            index += 1
        if start_separator_index is not None and end_separator_index is not None:
            messages_domain = "\n".join(lines[start_separator_index + 1 : end_separator_index])
        else:
            messages_domain = ""
        return cls(messages_domain)

    def _make_messages_with_separators(self) -> str:
        fragment = f"{self._LLM_MESSAGES_SEPARATOR_START}\n{self.messages_domain}\n{self._LLM_MESSAGES_SEPARATOR_END}\n"
        return fragment

    def create_patch(self, buffer_content: str) -> ReplaceLinesPatch | NoReplacePatch:
        lines = buffer_content.split("\n")
        index = 0
        start_separator_index = None
        end_separator_index = None
        while index < len(lines):
            if self._LLM_MESSAGES_SEPARATOR_START == lines[index].strip(" \t"):
                start_separator_index = index
                while index < len(lines):
                    if self._LLM_MESSAGES_SEPARATOR_END == lines[index].strip(" \t"):
                        end_separator_index = index
                        break
                    index += 1
                break
            index += 1
        if start_separator_index is not None and end_separator_index is not None:
            line_range = LineRange(start=start_separator_index + 1, end=end_separator_index)
            patch = ReplaceLinesPatch(line_range=line_range, lines=self.messages_domain.split("\n"))
        elif start_separator_index is not None:
            line_range = LineRange(start=start_separator_index, end=start_separator_index + 1)
            patch = ReplaceLinesPatch(line_range=line_range, lines=self._make_messages_with_separators().split("\n"))
        else:
            line_range = LineRange(start=len(lines), end=len(lines))
            patch = ReplaceLinesPatch(line_range=line_range, lines=self._make_messages_with_separators().split("\n"))
        return patch
