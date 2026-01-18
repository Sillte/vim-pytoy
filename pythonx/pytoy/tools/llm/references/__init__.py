from typing import Annotated, Literal, Self, assert_never, Protocol, Any  
from pathlib import Path

from pytoy.tools.llm.references.reference_collectors import ReferenceCollector # noqa:  # type: ignore
from pytoy.tools.llm.references.section_writer import ReferenceSectionWriter # noqa:  # type: ignore
from pytoy.tools.llm.references.models import InfoSource, ReferenceDataset #noqa: #type: ignore
from pytoy.tools.llm.references.converters import ConverterProtocol, MarkdownConverter, MarkItDownConverter # noqa: # type: ignore


class ReferenceHandler:
    def __init__(self, storage_folder: str | Path):
        self._storage_folder = Path(storage_folder)
        
    @property
    def storage_folder(self) -> Path:
        return self._storage_folder
    
    @property
    def exist_reference(self) -> bool:
        try:
            ReferenceDataset.load(self.storage_folder)
        except Exception:
            return False
        return True

        
    @property
    def collector(self) -> ReferenceCollector:
        return ReferenceCollector(self.storage_folder)
    
    @property
    def section_writer(self) -> ReferenceSectionWriter:
        dataset = ReferenceDataset.load(self.storage_folder)
        return ReferenceSectionWriter(dataset)

if __name__ == "__main__":
    pass

