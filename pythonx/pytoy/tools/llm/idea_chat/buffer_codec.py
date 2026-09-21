from dataclasses import dataclass
from typing import ClassVar, Self, Sequence

from pytoy.shared.lib.text import LineRange


@dataclass(frozen=True)
class ReplacePatch:
    line_range: LineRange
    lines: Sequence[str]


@dataclass(frozen=True)
class LLMBufferCodec:
    _LLM_MESSAGES_SEPARATOR_START: ClassVar[str] = "---LLMMessages-BEGIN---"
    _LLM_MESSAGES_SEPARATOR_END: ClassVar[str] = "---LLMMessages-END---"
    messages_domain: str | None = None

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
            messages_domain = None
        return cls(messages_domain)

    def to_buffer_content(self) -> str:
        if not self.valid:
            raise ValueError("This does not include `messages`.")
        fragment = f"{self._LLM_MESSAGES_SEPARATOR_START}\n{self.messages_domain}\n{self._LLM_MESSAGES_SEPARATOR_END}\n"
        return fragment

    def create_patch(self, buffer_content: str) -> ReplacePatch | None:
        if not self.valid:
            raise ValueError("This does not include `messages`.")
        if self.messages_domain is None:
            raise RuntimeError("This does not include `messages`.")

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
            return ReplacePatch(line_range=line_range, lines=self.messages_domain.split("\n"))
        return None

    @classmethod
    def provide_empty_domain(cls) -> str:
        return f"{cls._LLM_MESSAGES_SEPARATOR_START}\n{cls._LLM_MESSAGES_SEPARATOR_END}\n"

    @property
    def valid(self) -> bool:
        return self.messages_domain is not None
