from dataclasses import dataclass
from typing import Sequence, Literal


@dataclass(frozen=True)
class CodeBlock:
    type: Literal["python", "bash"] | str
    start: int   # 0-index lineno of `markdown`. "```" is not included.
    end: int  # 0-index lineno of `markdown`. exclusive. "```" is not included.
    lines: Sequence[str]


@dataclass(frozen=True)
class MarkdownStructure:
    code_blocks: Sequence[CodeBlock]

    def get_current_code_block(self, position: int) -> CodeBlock | None:
        for block in self.code_blocks:
            if block.start <= position < block.end:
                return block
        return None


class MarkdownExtractor:
    """Extract information of markdown
    """

    def __init__(self, markdown: str):
        self._markdown = markdown

    @property
    def markdown(self) -> str:
        return self._markdown

    @property
    def structure(self) -> MarkdownStructure:
        return MarkdownStructure(code_blocks=self.code_blocks)

    @property
    def code_blocks(self) -> Sequence[CodeBlock]:
        blocks = []
        lines = self.markdown.split("\n")
        type = None
        index = 0
        while index < len(lines):
            line = lines[index]
            if line.startswith("```"):
                type = self._normalize_type(line.strip("`").strip())
                index += 1
                block_lines = []
                start = index
                while index < len(lines):
                    line = lines[index]
                    if line.startswith("```"):
                        blocks.append(
                            CodeBlock(type=type, start=start, end=index, lines=block_lines))
                        break
                    else:
                        block_lines.append(lines[index])
                    index += 1
            index += 1
        return blocks

    def _normalize_type(self, type: str) -> str:
        maps = {"py": "python",
                "sh": "bash"}
        return maps.get(type, type)


if __name__ == "__main__":
    pass
