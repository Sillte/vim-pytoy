from pathlib import Path
from typing import Annotated, Literal, Self, assert_never, Protocol, Final, Sequence
from markitdown import MarkItDown

import requests
from pydantic import Field, BaseModel, field_validator
from pytoy.tools.llm.references.models import ReferenceDataset, ResourceUri, ReferenceInfo, Extension



class HTTPMarkItDownConverter:
    def __init__(self, impl: MarkItDown | None = None) -> None:
        if impl is None:
            impl = MarkItDown()
        self._impl = impl

    @property
    def extension(self) -> str | list[str]:
        # NOT YET.
        return [] 

    def to_markdown(self, uri: str) -> str:
        return self._impl.convert(uri).text_content


class ConverterProtocol(Protocol):
    # In case of callable,  
    @property
    def extension(self) -> str | list[str]: ...


    @property
    def preference(self) -> float:
        # 1- 100
        ...

    def to_markdown(self, path: Path) -> str: ...


class MarkdownConverter:
    @property
    def extension(self) -> list[str]:
        return [
            ".md",
            ".txt",
            ".py",
        ]

    @property
    def preference(self) -> float:
        return 100

    def to_markdown(self, path: Path) -> str:
        return Path(path).read_text()


class MarkItDownConverter:
    def __init__(self, impl: MarkItDown | None = None) -> None:
        if impl is None:
            impl = MarkItDown()
        self._impl: Final = impl

    @property
    def extension(self) -> str | list[str]:
        return [".docx", ".pptx", ".xlsx", ".pdf", ".json", ".yaml", ".yml", ".toml"]

    # Last resort
    @property
    def preference(self) -> float:
        return 0.1

    def to_markdown(self, path: Path) -> str:
        return self._impl.convert(path).text_content

class ReferenceConverterManager:
    _converters = [MarkdownConverter(), MarkItDownConverter()]
    def __init__(self):
        self._ext_to_converter = self._make_ext_to_converter(self._converters)


    @property
    def converters(self) -> list[ConverterProtocol]:
        return self._converters

    def pick(self, uri: ResourceUri) -> None | ConverterProtocol:
        key_extension = uri.extension
        return self._ext_to_converter.get(key_extension)
        
    
    def _make_ext_to_converter(self, converters: Sequence[ConverterProtocol]) -> dict[Extension, ConverterProtocol]:
        result = dict()
        for converter in sorted(converters, key=lambda con: con.preference, reverse=False):
            extension = converter.extension
            exs = [extension] if isinstance(extension, str) else extension
            for ex in exs:
                result[ex] = converter
        return result

